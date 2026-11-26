# autocomplete tokens (HTML autofill)

Spec: HTML Living Standard, "Autofill" (<https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#autofill>).
WCAG 1.3.5 lists the input purposes in section 7 of WCAG 2.2; they match these field names.

## Grammar

```
autocomplete = "on" | "off"
             | [section-NAME] [shipping | billing] [home | work | mobile | fax | pager] FIELD [webauthn]
```

- `section-NAME`: groups fields when a page has two of the same (e.g. two addresses).
- `shipping` / `billing`: which address or contact the field belongs to.
- `home` / `work` / `mobile` / `fax` / `pager`: only before `tel*`, `email`, `impp`.
- `webauthn`: last token, on `username` or `current-password` fields that should offer passkeys.
- Tokens are case-insensitive, separated by spaces. Exactly one field name.

## Field names

| Token | Use for |
| --- | --- |
| `name` | full name in one field |
| `honorific-prefix`, `given-name`, `additional-name`, `family-name`, `honorific-suffix` | split name fields (Mr, first, middle, last, Jr) |
| `nickname` | nickname, screen name |
| `username` | login name |
| `new-password` | sign-up, password change, confirmation field |
| `current-password` | login |
| `one-time-code` | SMS or email verification code |
| `organization-title`, `organization` | job title, company |
| `street-address` | whole street address in a textarea |
| `address-line1`, `address-line2`, `address-line3` | street address split over inputs |
| `address-level4` .. `address-level1` | most specific to least: `address-level2` = city/town, `address-level1` = state/province/region |
| `country`, `country-name` | country code (select values like `BD`) / country name |
| `postal-code` | postcode / ZIP |
| `cc-name`, `cc-given-name`, `cc-additional-name`, `cc-family-name` | name on card |
| `cc-number`, `cc-exp`, `cc-exp-month`, `cc-exp-year`, `cc-csc`, `cc-type` | card details |
| `transaction-currency`, `transaction-amount` | payment currency and amount |
| `language` | preferred language |
| `bday`, `bday-day`, `bday-month`, `bday-year` | birthday |
| `sex` | gender identity (free text) |
| `url`, `photo` | home page, avatar image URL |
| `tel`, `tel-country-code`, `tel-national`, `tel-area-code`, `tel-local`, `tel-local-prefix`, `tel-local-suffix`, `tel-extension` | phone (contact field: may follow home/work/mobile) |
| `email` | email (contact field) |
| `impp` | instant messaging URL (contact field) |

## Common mistakes

| Wrong | Right |
| --- | --- |
| `zip`, `postcode`, `postal_code` | `postal-code` |
| `surname`, `lastname`, `last-name` | `family-name` |
| `firstname`, `first-name` | `given-name` |
| `phone`, `mobile` | `tel` (or `mobile tel`) |
| `city` | `address-level2` |
| `state`, `province` | `address-level1` |
| `e-mail` | `email` |
| `password` | `current-password` or `new-password` |
| `mobile street-address` | `street-address` (contact types only before tel/email/impp) |
| `off` on name/email/address | the real token (1.3.5); keep `off` for fields that are not the user's own data, e.g. a search box or another person's details |

## Type and inputmode

| Field | `type` | Extra |
| --- | --- | --- |
| Email | `email` | `autocomplete="email"`, `spellcheck="false"` |
| Phone | `tel` | `autocomplete="tel"` |
| One-time code | `text` | `inputmode="numeric" autocomplete="one-time-code"` |
| Card number | `text` | `inputmode="numeric" autocomplete="cc-number"` (not `type=number`) |
| Postcode | `text` | `autocomplete="postal-code"` (not `type=number`: leading zeros, letters) |
| Date of birth | three text fields or `type="date"` | `bday-day`, `bday-month`, `bday-year` |
