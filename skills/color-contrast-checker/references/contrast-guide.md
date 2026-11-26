# Contrast guide (WCAG 2.2)

## Formula

Relative luminance of an sRGB colour, each channel `c` in 0..1:

```
c_lin = c / 12.92                      if c <= 0.04045
c_lin = ((c + 0.055) / 1.055) ** 2.4   otherwise
L = 0.2126 * R_lin + 0.7152 * G_lin + 0.0722 * B_lin
ratio = (L_lighter + 0.05) / (L_darker + 0.05)      # 1:1 .. 21:1
```

WCAG 2.2 uses 0.04045 (older text said 0.03928; the difference never changes a result).
Ratios are not rounded up: 4.499:1 fails 4.5:1.

Translucent colours are composited first: a 50% black text on white renders as `#808080`.
The script composites a translucent background over `--default-bg` (white by default).

## Thresholds

| Criterion | Applies to | Minimum |
| --- | --- | --- |
| 1.4.3 Contrast (Minimum), AA | text and images of text | 4.5:1; large text 3:1 |
| 1.4.6 Contrast (Enhanced), AAA | text | 7:1; large text 4.5:1 |
| 1.4.11 Non-text Contrast, AA | UI component boundaries and states, focus indicators, meaningful icons, chart lines/segments | 3:1 against adjacent colours |

Large text: at least 18pt (24 CSS px) regular, or 14pt (about 18.66 CSS px) bold
(font-weight 700+). `1.5rem` is treated as 24px (16px root); if the site changes the root
size, pass `--large` explicitly.

## Exempt

- Logos and brand names in text form that are part of a logo
- Incidental text: pure decoration, text in a photo that is not important, inactive
  (disabled) controls
- Text that is not visible to anyone

Not exempt, often missed: placeholder text, "muted" help text, footer text, error text on
tinted backgrounds, text on hover/focus states, visited links, and text in dark mode.

## Non-text contrast in practice

- Input borders: the border (or the field background if it differs from the page) needs
  3:1 against the page. Very light grey borders (`#e5e7eb` on white = 1.23:1) fail if
  the border is the only thing that shows where the field is.
- Focus indicator: 3:1 against the background next to it. A two-colour ring
  (`outline: 2px solid #fff; box-shadow: 0 0 0 4px #1a4fd6`) works on light and dark.
- Toggle/checkbox states: the checked vs unchecked difference must be perceivable without
  colour alone, and the parts that show state need 3:1.
- Charts: adjacent segments need 3:1 against each other or a separator/pattern.
- Icons that carry meaning (no text label) need 3:1; icons next to a text label are decorative.

## Links in text

If links are identified only by colour (no underline), WCAG technique G183 asks for 3:1
between link colour and surrounding text, plus a non-colour cue on hover and focus.
Simplest fix: keep underlines in body text.

## Picking accessible colours

- On white, the lightest grey that passes AA for normal text is `#767676` (4.54:1).
- On black, the darkest grey that passes is about `#757575`.
- Changing lightness while keeping hue and saturation (what the script suggests) keeps the
  brand feel. If a brand colour cannot pass for text, use it for large headings, borders
  (3:1) or backgrounds with dark text instead.
- Check every state in both light and dark themes: tokens such as `--text-muted` often pass
  in one and fail in the other.

## Where the numbers come from in a browser

- Chrome/Edge devtools: Elements > Styles > click a colour swatch: shows the contrast ratio
  and AA/AAA lines for the element's computed background.
- Firefox devtools: Accessibility panel > Check for issues > Contrast.
- For text over images, use the eyedropper on the lightest and darkest areas behind the text.
