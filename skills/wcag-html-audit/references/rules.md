# html_audit.py rules

Severity guide: **high** = blocks some users from content or a task; **medium** = makes
it noticeably harder; **low** = best practice or likely problem; **info** = review.

| Rule | Sev | WCAG | What it means | Typical fix | Known false positives |
| --- | --- | --- | --- | --- | --- |
| `html.lang_missing` | high | 3.1.1 | `<html>` has no `lang` | `<html lang="en">` | none |
| `html.lang_invalid` | high | 3.1.1 | `lang` is not BCP 47 (`english`, `en_US`) | `en`, `en-US`, `bn-BD` | none |
| `lang.invalid` | medium | 3.1.2 | invalid `lang` on a passage | fix the tag | none |
| `document.title_missing` | high | 2.4.2 | no or empty `<title>` | "Topic - Site" | templates that set the title in JS |
| `meta.viewport_zoom_blocked` | high | 1.4.4 | `user-scalable=no` or `maximum-scale` < 2 | remove both | none |
| `meta.refresh` | high | 2.2.1 | timed refresh/redirect | server redirect (delay 0 is ignored) | none |
| `img.alt_missing` | high | 1.1.1 | `<img>` without `alt` | describe it, or `alt=""` if decorative | images hidden by CSS only |
| `img.alt_placeholder` | medium | 1.1.1 | alt is a file name or "image" | real description | a product literally named "Logo" |
| `img.empty_alt_with_role` | medium | 1.1.1 | `alt=""` with a meaningful role | pick one | none |
| `img.alt_long` | info | 1.1.1 | alt over 150 characters | move detail to text or `<figcaption>` | complex images that need it |
| `input_image.alt_missing` | high | 1.1.1 | `<input type="image">` without alt | `alt="Search"` | none |
| `area.alt_missing` | high | 1.1.1 | image map area without alt | alt on each `<area>` | none |
| `svg.name_missing` | high | 1.1.1 | `<svg role="img">` without name | `<title>` or `aria-label`; decorative: `aria-hidden="true"` | none |
| `object.name_missing` | medium | 1.1.1 | `<object>`/`<embed>` without alternative | title + fallback content | none |
| `link.empty` | high | 2.4.4, 4.1.2 | link with no accessible name | text, alt on its image, `aria-label` | names added by JS |
| `link.generic_text` | low | 2.4.4 | "click here", "read more" | describe the target | context in the same sentence can pass 2.4.4 |
| `link.new_window` | info | 3.2.5 | `target=_blank` without warning | "(opens in new tab)" | 3.2.5 is AAA, so info only |
| `link.no_href` | high | 2.1.1 | `<a onclick>` without `href` | `<button type="button">` | none |
| `button.empty` | high | 4.1.2 | button without a name | text or `aria-label` | names added by JS |
| `form.label_missing` | high | 1.3.1, 4.1.2 | field without label (placeholder does not count) | `<label for>` | labels added by JS |
| `form.title_only_label` | low | 3.3.2 | label only in `title` tooltip | visible label | none |
| `label.for_missing_target` | medium | 1.3.1 | `<label for>` matches no id | fix the id | none |
| `heading.empty` | high | 1.3.1, 2.4.6 | empty heading | remove or fill | headings filled by JS |
| `heading.skipped_level` | medium | 1.3.1 | h2 followed by h4 | use the next level | widget fragments audited alone |
| `heading.no_h1` / `heading.none` | low | 1.3.1, 2.4.6 | no h1 / no headings | add them | none |
| `id.duplicate` | high/medium | 1.3.1, 4.1.2 | same id twice (high when referenced by `for`/ARIA) | unique ids | none (4.1.1 Parsing is obsolete in 2.2, but broken references still fail 1.3.1/4.1.2) |
| `tabindex.positive` | medium | 2.4.3 | `tabindex` > 0 | `0` and DOM order | none |
| `iframe.title_missing` | high | 4.1.2 | iframe without title | `title="Map of our office"` | hidden tracking iframes (add `aria-hidden` + `tabindex=-1`) |
| `table.no_headers` | high | 1.3.1 | data table without `th` | `<th scope>`; layout table: `role="presentation"` | layout tables without role |
| `table.no_caption` | info | 1.3.1 | data table without caption | `<caption>` | heading right before the table |
| `media.autoplay_sound` | high | 1.4.2 | autoplay without `muted` | remove autoplay or add `muted` + controls | audio under 3 seconds |
| `media.autoplay_no_controls` | medium | 2.2.2 | muted autoplay video without controls | `controls` or a pause button | videos under 5 seconds |
| `media.no_captions` | medium | 1.2.2 | `<video>` without captions track | WebVTT captions | no speech; captions burned in; player adds tracks in JS |
| `element.moving_content` | high | 2.2.2 | `<marquee>`/`<blink>` | remove | none |
| `landmark.main_missing` | low | 1.3.1, 2.4.1 | no `<main>` | wrap content in `<main>` | fragments |

Pages without `<html>` are treated as fragments (components, partials): document checks
(lang, title, main, h1) are skipped.

## Limits

- No CSS: anything hidden with a class (`.sr-only`, `.d-none`) still counts as visible;
  only `hidden`, `aria-hidden="true"`, inline `display:none`/`visibility:hidden` are known.
- No JavaScript: audit the rendered DOM for SPAs.
- The accessible name computation is simplified (no CSS `::before` content, no
  `aria-owns`, no shadow DOM). When in doubt, check the browser's accessibility tree
  (Chrome devtools > Elements > Accessibility pane).
