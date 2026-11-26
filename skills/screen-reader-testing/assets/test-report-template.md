# Screen reader test report

| Field | Value |
| --- | --- |
| Product / URL or build | |
| Pages / flows tested | |
| Tester | |
| Date | |
| Combinations | e.g. NVDA 2025.x + Firefox 14x (Windows 11); VoiceOver + Safari (macOS 15); VoiceOver + Safari (iOS 18) |
| Plan | created with `sr_outline.py --format markdown` (attach) |

## Summary

- Blockers: 0, High: 0, Medium: 0, Low: 0
- Overall: can a screen reader user complete the main tasks? (yes / with difficulty / no)

## Findings

### 1. Short title of the problem

| Field | Value |
| --- | --- |
| Severity | Blocker / High / Medium / Low |
| WCAG | e.g. 4.1.2 Name, Role, Value (A) |
| Where | page, component, selector or line |
| Combination | NVDA + Chrome (also VoiceOver + Safari?) |

**Steps**

1. Open ...
2. Press Tab until ...
3. Press Enter

**Announced**: "button" (quote the speech viewer / caption panel)

**Expected**: "Close dialog, button"

**Suggested fix**: add `aria-label="Close dialog"` to the icon button, or visible text.

---

## Passed checks

| Scenario | Result | Notes |
| --- | --- | --- |
| Page title | pass | |
| Landmarks | pass | |
