#!/usr/bin/env python3
"""Compute WCAG 2.2 contrast ratios for colour pairs, pair files or simple CSS (offline).

Modes:
  contrast.py FG BG                 one pair, e.g. "#767676" white, "rgb(0 0 0 / .6)" "#fff"
  contrast.py --pairs pairs.txt     one "fg, bg[, label]" per line (# comments allowed)
  contrast.py --css styles.css      rules that set color (and background) in the same block;
                                    resolves var(--x) from :root, reads font-size/weight
                                    for the large-text threshold

Thresholds (WCAG 2.2): text AA 4.5:1 (large 3:1), text AAA 7:1 (large 4.5:1),
non-text UI components and graphics 3:1 (1.4.11). Large text = at least 24px (18pt)
or at least 18.66px (14pt) bold. Ratios are never rounded up: 4.49:1 fails AA.

Exit codes: 0 = everything passes the requested level, 1 = at least one failure, 2 = error.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys
from pathlib import Path

NAMED = {
    "aliceblue": "f0f8ff", "antiquewhite": "faebd7", "aqua": "00ffff", "aquamarine": "7fffd4", "azure": "f0ffff",
    "beige": "f5f5dc", "bisque": "ffe4c4", "black": "000000", "blanchedalmond": "ffebcd", "blue": "0000ff",
    "blueviolet": "8a2be2", "brown": "a52a2a", "burlywood": "deb887", "cadetblue": "5f9ea0", "chartreuse": "7fff00",
    "chocolate": "d2691e", "coral": "ff7f50", "cornflowerblue": "6495ed", "cornsilk": "fff8dc", "crimson": "dc143c",
    "cyan": "00ffff", "darkblue": "00008b", "darkcyan": "008b8b", "darkgoldenrod": "b8860b", "darkgray": "a9a9a9",
    "darkgreen": "006400", "darkgrey": "a9a9a9", "darkkhaki": "bdb76b", "darkmagenta": "8b008b",
    "darkolivegreen": "556b2f", "darkorange": "ff8c00", "darkorchid": "9932cc", "darkred": "8b0000",
    "darksalmon": "e9967a", "darkseagreen": "8fbc8f", "darkslateblue": "483d8b", "darkslategray": "2f4f4f",
    "darkslategrey": "2f4f4f", "darkturquoise": "00ced1", "darkviolet": "9400d3", "deeppink": "ff1493",
    "deepskyblue": "00bfff", "dimgray": "696969", "dimgrey": "696969", "dodgerblue": "1e90ff",
    "firebrick": "b22222", "floralwhite": "fffaf0", "forestgreen": "228b22", "fuchsia": "ff00ff",
    "gainsboro": "dcdcdc", "ghostwhite": "f8f8ff", "gold": "ffd700", "goldenrod": "daa520", "gray": "808080",
    "green": "008000", "greenyellow": "adff2f", "grey": "808080", "honeydew": "f0fff0", "hotpink": "ff69b4",
    "indianred": "cd5c5c", "indigo": "4b0082", "ivory": "fffff0", "khaki": "f0e68c", "lavender": "e6e6fa",
    "lavenderblush": "fff0f5", "lawngreen": "7cfc00", "lemonchiffon": "fffacd", "lightblue": "add8e6",
    "lightcoral": "f08080", "lightcyan": "e0ffff", "lightgoldenrodyellow": "fafad2", "lightgray": "d3d3d3",
    "lightgreen": "90ee90", "lightgrey": "d3d3d3", "lightpink": "ffb6c1", "lightsalmon": "ffa07a",
    "lightseagreen": "20b2aa", "lightskyblue": "87cefa", "lightslategray": "778899", "lightslategrey": "778899",
    "lightsteelblue": "b0c4de", "lightyellow": "ffffe0", "lime": "00ff00", "limegreen": "32cd32", "linen": "faf0e6",
    "magenta": "ff00ff", "maroon": "800000", "mediumaquamarine": "66cdaa", "mediumblue": "0000cd",
    "mediumorchid": "ba55d3", "mediumpurple": "9370db", "mediumseagreen": "3cb371", "mediumslateblue": "7b68ee",
    "mediumspringgreen": "00fa9a", "mediumturquoise": "48d1cc", "mediumvioletred": "c71585",
    "midnightblue": "191970", "mintcream": "f5fffa", "mistyrose": "ffe4e1", "moccasin": "ffe4b5",
    "navajowhite": "ffdead", "navy": "000080", "oldlace": "fdf5e6", "olive": "808000", "olivedrab": "6b8e23",
    "orange": "ffa500", "orangered": "ff4500", "orchid": "da70d6", "palegoldenrod": "eee8aa", "palegreen": "98fb98",
    "paleturquoise": "afeeee", "palevioletred": "db7093", "papayawhip": "ffefd5", "peachpuff": "ffdab9",
    "peru": "cd853f", "pink": "ffc0cb", "plum": "dda0dd", "powderblue": "b0e0e6", "purple": "800080",
    "rebeccapurple": "663399", "red": "ff0000", "rosybrown": "bc8f8f", "royalblue": "4169e1",
    "saddlebrown": "8b4513", "salmon": "fa8072", "sandybrown": "f4a460", "seagreen": "2e8b57",
    "seashell": "fff5ee", "sienna": "a0522d", "silver": "c0c0c0", "skyblue": "87ceeb", "slateblue": "6a5acd",
    "slategray": "708090", "slategrey": "708090", "snow": "fffafa", "springgreen": "00ff7f",
    "steelblue": "4682b4", "tan": "d2b48c", "teal": "008080", "thistle": "d8bfd8", "tomato": "ff6347",
    "turquoise": "40e0d0", "violet": "ee82ee", "wheat": "f5deb3", "white": "ffffff", "whitesmoke": "f5f5f5",
    "yellow": "ffff00", "yellowgreen": "9acd32",
}  # fmt: skip

THRESHOLDS = {"AA": (4.5, 3.0), "AAA": (7.0, 4.5)}
UI_THRESHOLD = 3.0


class ColorError(ValueError):
    pass


def _num(token: str, scale: float) -> float:
    token = token.strip()
    if token.endswith("%"):
        return float(token[:-1]) / 100 * scale
    return float(token)


def parse_color(value: str) -> tuple[float, float, float, float]:
    """Parse a CSS colour into (r, g, b, a) with r,g,b in 0-255 and a in 0-1."""
    v = value.strip().lower()
    if v in NAMED:
        v = "#" + NAMED[v]
    if v == "transparent":
        return (0.0, 0.0, 0.0, 0.0)
    m = re.fullmatch(r"#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})", v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (float(r), float(g), float(b), a)
    m = re.fullmatch(r"(rgba?|hsla?)\((.*)\)", v)
    if not m:
        raise ColorError(f"unsupported colour: {value!r}")
    fn, inner = m.group(1), m.group(2)
    if "/" in inner:
        main, alpha = inner.split("/", 1)
        parts = re.split(r"[\s,]+", main.strip())
        parts.append(alpha.strip())
    else:
        parts = [p for p in re.split(r"[\s,]+", inner.strip()) if p]
    if len(parts) not in (3, 4):
        raise ColorError(f"cannot parse {value!r}")
    try:
        a = _num(parts[3], 1.0) if len(parts) == 4 else 1.0
        if fn.startswith("rgb"):
            r, g, b = (_num(p, 255.0) for p in parts[:3])
        else:
            hue = float(parts[0].replace("deg", ""))
            sat = _num(parts[1] if parts[1].endswith("%") else parts[1] + "%", 1.0)
            light = _num(parts[2] if parts[2].endswith("%") else parts[2] + "%", 1.0)
            rr, gg, bb = colorsys.hls_to_rgb((hue % 360) / 360, light, sat)
            r, g, b = rr * 255, gg * 255, bb * 255
    except ValueError as exc:
        raise ColorError(f"cannot parse {value!r}") from exc
    clamp = lambda x, hi: max(0.0, min(hi, x))  # noqa: E731
    return (clamp(r, 255), clamp(g, 255), clamp(b, 255), clamp(a, 1.0))


def blend(fg: tuple, bg: tuple) -> tuple[float, float, float]:
    """Composite a (possibly translucent) foreground over an opaque background."""
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def luminance(rgb: tuple) -> float:
    def chan(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str, base: str = "#ffffff") -> float:
    fgc, bgc, basec = parse_color(fg), parse_color(bg), parse_color(base)
    bg_rgb = blend(bgc, (*basec[:3], 1.0))
    fg_rgb = blend(fgc, (*bg_rgb, 1.0))
    l1, l2 = sorted((luminance(fg_rgb), luminance(bg_rgb)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def floor2(x: float) -> float:
    return int(x * 100) / 100


def to_hex(rgb: tuple) -> str:
    return "#" + "".join(f"{round(c):02x}" for c in rgb[:3])


def suggest(fg: str, bg: str, target: float) -> str | None:
    """Nearest foreground (same hue/saturation, changed lightness) that reaches target."""
    r, g, b, _ = parse_color(fg)
    h, light, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    best = None
    for step in range(1, 101):
        for direction in (-1, 1):
            nl = light + direction * step / 100
            if not 0 <= nl <= 1:
                continue
            rgb = tuple(c * 255 for c in colorsys.hls_to_rgb(h, nl, s))
            cand = to_hex(rgb)
            if ratio(cand, bg) >= target:
                best = cand
                break
        if best:
            return best
    return None


def opaque_fg(fg: str, bg: str, base: str = "#ffffff") -> str:
    """The solid colour a translucent foreground actually renders as."""
    fgc = parse_color(fg)
    if fgc[3] >= 1:
        return fg
    bg_rgb = blend(parse_color(bg), (*parse_color(base)[:3], 1.0))
    return to_hex(blend(fgc, (*bg_rgb, 1.0)))


def evaluate(fg: str, bg: str, label: str = "", large: bool = False, level: str = "AA", base: str = "#ffffff") -> dict:
    rt = ratio(fg, bg, base)
    shown = floor2(rt)
    normal_need, large_need = THRESHOLDS[level]
    need = large_need if large else normal_need
    result = {
        "label": label,
        "foreground": fg,
        "background": bg,
        "ratio": shown,
        "large_text": large,
        "AA_normal": rt >= 4.5,
        "AA_large": rt >= 3.0,
        "AAA_normal": rt >= 7.0,
        "AAA_large": rt >= 4.5,
        "ui_component": rt >= UI_THRESHOLD,
        "level": level,
        "required": need,
        "pass": rt >= need,
    }
    if not result["pass"]:
        result["suggested_foreground"] = suggest(opaque_fg(fg, bg, base), bg, need)
        if parse_color(bg)[3] >= 1:
            result["suggested_background"] = suggest(bg, opaque_fg(fg, bg, base), need)
    if parse_color(fg)[3] < 1 or parse_color(bg)[3] < 1:
        result["note"] = "translucent colour composited over " + ("the background" if parse_color(bg)[3] == 1 else base)
    return result


# ---------------------------------------------------------------- CSS extraction

COLOR_TOKEN = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\([^)]*\)|\b(?:"
    + "|".join(sorted(NAMED, key=len, reverse=True))
    + r"|transparent)\b",
    re.I,
)


def css_blocks(css: str):
    """Yield (selector, declarations, line) for every rule, flattening @media/@supports."""
    css = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)
    stack: list[tuple[str, int]] = []
    buf_start = 0
    i = 0
    while i < len(css):
        ch = css[i]
        if ch == "{":
            selector = css[buf_start:i].strip()
            stack.append((selector, i))
            buf_start = i + 1
        elif ch == "}":
            if stack:
                selector, open_at = stack.pop()
                body = css[open_at + 1 : i]
                if "{" not in body and not selector.startswith("@"):
                    line = css.count("\n", 0, open_at) + 1
                    decls = {}
                    for decl in body.split(";"):
                        if ":" in decl:
                            k, v = decl.split(":", 1)
                            decls[k.strip().lower()] = re.sub(r"\s*!important\s*$", "", v.strip(), flags=re.I)
                    yield selector.split(";")[-1].strip(), decls, line
            buf_start = i + 1
        elif ch == ";" and not stack:
            buf_start = i + 1
        i += 1


def resolve_vars(value: str, variables: dict, depth: int = 0) -> str:
    if depth > 10:
        return value

    def sub(m):
        name, fallback = m.group(1), m.group(2)
        if name in variables:
            return resolve_vars(variables[name], variables, depth + 1)
        return fallback.strip() if fallback else m.group(0)

    return re.sub(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^)]*\))?[^()]*))?\)", sub, value)


def font_px(value: str | None) -> float | None:
    if not value:
        return None
    m = re.match(r"([\d.]+)\s*(px|pt|rem|em|%)?", value.strip())
    if not m:
        return {"xx-large": 32, "x-large": 24, "large": 18, "medium": 16, "small": 13}.get(value.strip())
    n, unit = float(m.group(1)), (m.group(2) or "px")
    return {"px": n, "pt": n * 4 / 3, "rem": n * 16, "em": n * 16, "%": n * 16 / 100}[unit]


def is_large(size_px: float | None, weight: str | None) -> bool:
    if size_px is None:
        return False
    w = (weight or "400").strip().lower()
    bold = w in ("bold", "bolder") or (w.isdigit() and int(w) >= 700)
    return size_px >= 24 or (bold and size_px >= 18.66)


def pairs_from_css(css: str, default_bg: str) -> list[dict]:
    blocks = list(css_blocks(css))
    variables: dict = {}
    for sel, decls, _ in blocks:
        if sel in (":root", "html", ":host", "body") or sel.startswith(":root"):
            variables.update({k: v for k, v in decls.items() if k.startswith("--")})
    page_bg = default_bg
    for sel, decls, _ in blocks:
        if sel in ("body", "html", ":root"):
            bg_raw = resolve_vars(decls.get("background-color") or decls.get("background") or "", variables)
            m = COLOR_TOKEN.search(bg_raw)
            if m and "url(" not in bg_raw and "gradient" not in bg_raw:
                page_bg = m.group(0)
    out = []
    for sel, decls, line in blocks:
        if "color" not in decls:
            continue
        fg_raw = resolve_vars(decls["color"], variables)
        fgm = COLOR_TOKEN.fullmatch(fg_raw.strip())
        if not fgm:
            out.append({"selector": sel, "line": line, "skipped": f"color '{decls['color']}' not resolvable"})
            continue
        bg_raw = resolve_vars(decls.get("background-color") or decls.get("background") or "", variables)
        assumed = False
        if "gradient" in bg_raw or "url(" in bg_raw:
            out.append({"selector": sel, "line": line, "skipped": "background is an image/gradient: check manually"})
            continue
        bgm = COLOR_TOKEN.search(bg_raw) if bg_raw else None
        bg = bgm.group(0) if bgm else page_bg
        assumed = bgm is None
        size = font_px(resolve_vars(decls.get("font-size", ""), variables) or None)
        weight = resolve_vars(decls.get("font-weight", ""), variables) or None
        out.append(
            {
                "selector": sel,
                "line": line,
                "fg": fgm.group(0),
                "bg": bg,
                "bg_assumed": assumed,
                "large": is_large(size, weight),
            }
        )
    return out


def read_pairs(text: str) -> list[tuple[str, str, str]]:
    pairs = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or (line.startswith("#") and not re.match(r"#[0-9a-fA-F]{3,8}\s*,", line)):
            continue
        # split on commas that are not inside parentheses
        parts, depth, cur = [], 0, ""
        for ch in line:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append(cur.strip())
                cur = ""
            else:
                cur += ch
        parts.append(cur.strip())
        if len(parts) < 2:
            raise ColorError(f"expected 'fg, bg[, label]': {raw!r}")
        pairs.append((parts[0], parts[1], ", ".join(parts[2:])))
    return pairs


def print_text(results: list[dict], skipped: list[dict]) -> None:
    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        where = f"{r['label']}: " if r["label"] else ""
        size = "non-text/UI, 1.4.11" if r.get("ui") else ("large text" if r["large_text"] else "normal text")
        print(
            f"{mark} {where}{r['foreground']} on {r['background']} = {r['ratio']:.2f}:1 ({size}, "
            f"{r['level']} needs {r['required']}:1)"
        )
        print(
            "     AA normal {} | AA large {} | AAA normal {} | AAA large {} | UI/graphics 3:1 {}".format(
                *("yes" if r[k] else "no" for k in ("AA_normal", "AA_large", "AAA_normal", "AAA_large", "ui_component"))
            )
        )
        if r.get("bg_assumed"):
            print("     background not set in this rule: assumed page background; verify in the browser")
        if r.get("note"):
            print(f"     {r['note']}")
        if not r["pass"]:
            sug, sbg = r.get("suggested_foreground"), r.get("suggested_background")
            if sug:
                print(f"     suggestion: foreground {sug} on {r['background']} reaches {r['required']}:1")
            if sbg:
                print(f"     or keep the foreground and use background {sbg}")
            if not sug and not sbg:
                print("     no lightness change of either colour reaches the target; pick a different pair")
    for s in skipped:
        print(f"SKIP {s['selector']} (line {s['line']}): {s['skipped']}")
    failed = sum(1 for r in results if not r["pass"])
    print(f"\n{len(results)} pair(s), {failed} failing" + (f", {len(skipped)} skipped" if skipped else ""))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="WCAG 2.2 contrast ratios for colour pairs, pair files or simple CSS.",
        epilog="Examples: contrast.py '#767676' '#ffffff' | contrast.py --pairs pairs.txt --level AAA | "
        "contrast.py --css site.css --json. Exit 0 = all pass, 1 = failures, 2 = error.",
    )
    p.add_argument("colors", nargs="*", help="FG BG (hex, rgb(), hsl(), named)")
    p.add_argument("--pairs", help="file with 'fg, bg[, label]' per line, or - for stdin")
    p.add_argument("--css", help="CSS file to extract color/background pairs from")
    p.add_argument("--level", choices=["AA", "AAA"], default="AA", help="conformance level to enforce (default AA)")
    p.add_argument("--large", action="store_true", help="treat pairs as large text (>=24px or >=18.66px bold)")
    p.add_argument("--ui", action="store_true", help="non-text contrast (icons, borders, focus rings): 3:1")
    p.add_argument("--default-bg", default="#ffffff", help="page background when a CSS rule sets none")
    p.add_argument("--json", action="store_true", help="print JSON")
    args = p.parse_args(argv)

    jobs: list[tuple[str, str, str, bool, bool]] = []  # fg, bg, label, large, assumed
    skipped: list[dict] = []
    try:
        if args.colors:
            if len(args.colors) != 2:
                p.error("give exactly two colours: FG BG")
            jobs.append((args.colors[0], args.colors[1], "", args.large, False))
        if args.pairs:
            text = sys.stdin.read() if args.pairs == "-" else Path(args.pairs).read_text(encoding="utf-8")
            jobs += [(f, b, lab, args.large, False) for f, b, lab in read_pairs(text)]
        if args.css:
            for item in pairs_from_css(Path(args.css).read_text(encoding="utf-8"), args.default_bg):
                if "skipped" in item:
                    skipped.append(item)
                else:
                    label = f"{item['selector']} (line {item['line']})"
                    jobs.append((item["fg"], item["bg"], label, item["large"] or args.large, item["bg_assumed"]))
        if not jobs and not skipped:
            p.error("nothing to check: give FG BG, --pairs or --css")
        results = []
        for fg, bg, label, large, assumed in jobs:
            r = evaluate(fg, bg, label, large, args.level, args.default_bg)
            if args.ui:
                r["required"], r["pass"], r["ui"] = UI_THRESHOLD, r["ui_component"], True
                r.pop("suggested_foreground", None)
                r.pop("suggested_background", None)
                if not r["pass"]:
                    solid = opaque_fg(fg, bg, args.default_bg)
                    r["suggested_foreground"] = suggest(solid, bg, UI_THRESHOLD)
                    if parse_color(bg)[3] >= 1:
                        r["suggested_background"] = suggest(bg, solid, UI_THRESHOLD)
            if assumed:
                r["bg_assumed"] = True
            results.append(r)
    except (OSError, ColorError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"results": results, "skipped": skipped}, indent=2))
    else:
        print_text(results, skipped)
    return 0 if all(r["pass"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
