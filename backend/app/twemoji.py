"""Convert emoji characters to inlined Twemoji SVG paths.

Why this module exists
~~~~~~~~~~~~~~~~~~~~~~
Cricut Design Space (and CairoSVG's PNG backend) silently drop
``<text>`` elements that rely on system fonts. Colour-emoji fonts make
this even worse: even browsers that do render colour glyphs as bitmaps
won't help us when the artwork has to survive Cricut's Print-Then-Cut
pipeline. The robust answer — the same one we use for normal aufgaben
text in :mod:`text_to_path` — is to embed each emoji as **vector
paths** inline in the SVG. We use the Twitter Twemoji glyph set
because it is openly licensed (CC-BY 4.0), already shipped as clean
SVG, and the de-facto standard fallback that every other major
project uses.

How it works
~~~~~~~~~~~~
1. The first time an emoji is requested we map its codepoint sequence
   to a Twemoji filename (``1f3e0.svg`` for 🏠) using the same
   ``toCodePoint`` rules the official Twemoji JS lib uses (drop
   ``U+FE0F`` variation selectors, lowercase hex, dash-separated).
2. We try to read the cached SVG from disk. If it is missing we fetch
   it from the jsdelivr CDN and persist it to the cache directory.
3. The SVG is parsed once with ``xml.etree``; we keep just the inner
   markup (everything inside the root ``<svg>``) and the original
   viewBox.
4. :func:`render_emoji_group` returns a ``<g transform=...>`` element
   that places the emoji centred on ``(cx, cy)`` and scaled to the
   given square size. The caller drops it straight into the print
   layer, where it ends up as ordinary SVG paths — exactly what
   Cricut Print-Then-Cut and CairoSVG both handle reliably.

Failure mode
~~~~~~~~~~~~
If the CDN is unreachable and the emoji is not yet cached,
:func:`render_emoji_group` returns ``None``. The caller is expected
to fall back to a plain ``<text>`` element so at least the browser
preview stays informative.
"""
from __future__ import annotations

import logging
import os
import re
import ssl
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# jsdelivr mirrors the Twemoji repo. The version is pinned so we get a
# deterministic glyph set regardless of upstream churn. Twemoji 14.0.2
# is the last release before Twitter took the project down; the assets
# are stable.
_TWEMOJI_VERSION = "14.0.2"
_CDN_URL = (
    "https://cdn.jsdelivr.net/gh/jdecked/twemoji@{ver}/assets/svg/{name}.svg"
)

_DEFAULT_CACHE = Path(
    os.environ.get(
        "TWEMOJI_CACHE_DIR",
        os.path.join(
            os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
            "wheel-gen",
            "twemoji",
        ),
    )
)

_FETCH_TIMEOUT_S = 4.0
# Twemoji files are small (~3-15KB) but we keep a generous ceiling to
# guard against accidental redirects to large pages.
_FETCH_MAX_BYTES = 256 * 1024

_VS16 = 0xFE0F  # variation selector — Twemoji filenames omit it.
_SVG_NS_RE = re.compile(r' xmlns(?::[^=]+)?="[^"]*"')


@dataclass(frozen=True)
class _ParsedEmoji:
    inner: str
    viewbox: tuple[float, float, float, float]


def _emoji_to_codepoints(emoji: str) -> str | None:
    """Return the Twemoji filename stem for ``emoji`` (e.g. ``"1f3e0"``).

    Mirrors the official Twemoji ``toCodePoint`` helper:
    every Unicode scalar is rendered as lowercase hex and joined with
    ``-``; ``U+FE0F`` (text/emoji variation selector) is stripped, since
    Twemoji's filenames are keyed on the bare presentation form.
    """
    if not emoji:
        return None
    parts = [format(ord(c), "x") for c in emoji if ord(c) != _VS16]
    if not parts:
        # Pathological case: the emoji was *only* a variation selector.
        # Fall back to the raw codepoint so we at least try a fetch.
        parts = [format(ord(emoji[0]), "x")]
    return "-".join(parts)


def _cache_dir() -> Path:
    _DEFAULT_CACHE.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_CACHE


def _read_cached(name: str) -> str | None:
    path = _cache_dir() / f"{name}.svg"
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None
    return None


def _write_cached(name: str, data: str) -> None:
    path = _cache_dir() / f"{name}.svg"
    try:
        path.write_text(data, encoding="utf-8")
    except OSError as exc:  # pragma: no cover - cache is best-effort
        logger.warning("Failed to write Twemoji cache for %s: %s", name, exc)


@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext:
    """Build an SSL context that works on Linux *and* on the
    Python.org macOS build (which ships without a system CA bundle).

    We try the system default first, then ``certifi`` if it's
    importable. As a last resort we accept untrusted certs for the
    Twemoji CDN — these are public CC-BY-4.0 SVG assets so the only
    risk of a MITM is replacing one cartoon house with another, which
    is acceptable for a strictly developer-tool fallback.
    """
    try:
        return ssl.create_default_context()
    except ssl.SSLError:
        pass
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # pragma: no cover - best-effort
        pass
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _fetch_svg(name: str) -> str | None:
    url = _CDN_URL.format(ver=_TWEMOJI_VERSION, name=name)

    def _try(ctx: ssl.SSLContext | None) -> str | None:
        try:
            with urllib.request.urlopen(
                url, timeout=_FETCH_TIMEOUT_S, context=ctx
            ) as resp:
                if resp.status != 200:
                    return None
                data = resp.read(_FETCH_MAX_BYTES + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # Caller decides whether to retry with a different SSL
            # context; we just propagate the cause.
            raise exc
        if len(data) > _FETCH_MAX_BYTES:
            logger.warning("Twemoji fetch for %s exceeded size limit", name)
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None

    try:
        return _try(_ssl_context())
    except urllib.error.URLError as exc:
        # On the macOS Python.org build the system context can't find
        # any CA. Retry with a permissive context as a last-ditch dev
        # fallback so the local preview still shows real glyphs.
        if isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError):
            unverified = ssl.create_default_context()
            unverified.check_hostname = False
            unverified.verify_mode = ssl.CERT_NONE
            try:
                return _try(unverified)
            except (urllib.error.URLError, TimeoutError, OSError) as inner:
                logger.warning(
                    "Twemoji fetch failed for %s (insecure retry): %s",
                    name,
                    inner,
                )
                return None
        logger.warning("Twemoji fetch failed for %s: %s", name, exc)
        return None
    except (TimeoutError, OSError) as exc:
        logger.warning("Twemoji fetch failed for %s: %s", name, exc)
        return None


def _parse_svg(svg_text: str) -> _ParsedEmoji | None:
    # Twemoji files use the SVG default namespace. We strip namespaces
    # before parsing so the emitted markup is namespace-free and slots
    # straight into the parent SVG without polluting it with a second
    # ``xmlns="…/svg"`` declaration on every child element.
    cleaned = _SVG_NS_RE.sub("", svg_text)
    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as exc:
        logger.warning("Twemoji SVG parse error: %s", exc)
        return None

    vb = root.attrib.get("viewBox")
    if vb:
        try:
            x, y, w, h = (float(v) for v in vb.replace(",", " ").split())
        except ValueError:
            x, y, w, h = 0.0, 0.0, 36.0, 36.0
    else:
        # Twemoji's modern SVGs all set a viewBox; fall back to the
        # historical 36x36 grid just in case.
        x, y, w, h = 0.0, 0.0, 36.0, 36.0

    inner_parts: list[str] = []
    for child in list(root):
        inner_parts.append(ET.tostring(child, encoding="unicode"))
    return _ParsedEmoji(inner="".join(inner_parts), viewbox=(x, y, w, h))


@lru_cache(maxsize=512)
def _load_emoji(emoji: str) -> _ParsedEmoji | None:
    name = _emoji_to_codepoints(emoji)
    if not name:
        return None
    svg = _read_cached(name)
    if svg is None:
        svg = _fetch_svg(name)
        if svg is not None:
            _write_cached(name, svg)
    if svg is None:
        return None
    return _parse_svg(svg)


def is_known(emoji: str) -> bool:
    """Best-effort check: does this emoji resolve to a Twemoji glyph?"""
    return _load_emoji(emoji) is not None


def render_emoji_group(
    emoji: str,
    cx: float,
    cy: float,
    box_size: float,
    rotation_deg: float = 0.0,
) -> str | None:
    """Return an inlined ``<g>`` that draws ``emoji`` centred on
    ``(cx, cy)``, scaled to fit a ``box_size`` × ``box_size`` square,
    and rotated by ``rotation_deg``.

    Coordinates are in the same units as the surrounding SVG. Returns
    ``None`` when the emoji could not be loaded so the caller can fall
    back to a different presentation.
    """
    parsed = _load_emoji(emoji)
    if parsed is None:
        return None
    vb_x, vb_y, vb_w, vb_h = parsed.viewbox
    if vb_w <= 0 or vb_h <= 0:
        return None
    scale = box_size / max(vb_w, vb_h)
    # The emoji's own viewBox origin is rarely exactly (0,0), so we
    # shift by the viewBox top-left and then offset by half the box so
    # it ends up centred. The translate(cx,cy) + rotate happens on the
    # *outside* so the rotation pivots through the visual centre.
    return (
        f'<g transform="translate({cx:.4f} {cy:.4f}) '
        f'rotate({rotation_deg:.4f}) '
        f'scale({scale:.6f}) '
        f'translate({-vb_x - vb_w / 2.0:.4f} {-vb_y - vb_h / 2.0:.4f})">'
        f"{parsed.inner}</g>"
    )
