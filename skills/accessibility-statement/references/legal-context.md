# Regional context for accessibility statements

Orientation only, not legal advice. Laws, deadlines and referenced standards change; check
the official sources linked here and have the final text reviewed by whoever owns
compliance.

## European Union

- **Web Accessibility Directive (EU) 2016/2102**: public sector websites and apps. Requires
  an accessibility statement following the model in Commission Implementing Decision
  (EU) 2018/1523: conformance status, non-accessible content and reasons (including
  "disproportionate burden"), how to give feedback, a link to the enforcement procedure,
  and the date and method of the assessment. The standard is EN 301 549, which currently
  references WCAG 2.1 AA; aiming for WCAG 2.2 AA covers it.
  <https://digital-strategy.ec.europa.eu/en/policies/web-accessibility>
- **European Accessibility Act, Directive (EU) 2019/882**: applies from 28 June 2025 to
  many private-sector products and services, including e-commerce, banking, e-books,
  transport ticketing and electronic communications. Microenterprises providing services
  are exempt. Service providers must publish information on how the service meets the
  accessibility requirements (often done as an accessibility statement). National laws
  implement the details and enforcement.
  <https://ec.europa.eu/social/main.jsp?catId=1202>

The `enforcement` field in the config is where the member-state enforcement body and
procedure go.

## United Kingdom

- **Public Sector Bodies (Websites and Mobile Applications) Accessibility Regulations 2018**:
  public sector sites must meet WCAG 2.2 AA (as monitored by GDS since October 2024) and
  publish a statement in the GOV.UK sample format, including the enforcement paragraph
  referring to the Equality and Human Rights Commission (Great Britain) or the Equality
  Commission for Northern Ireland.
  <https://www.gov.uk/guidance/accessibility-requirements-for-public-sector-websites-and-apps>
- Private organisations: the Equality Act 2010 duty to make reasonable adjustments applies;
  a statement is good practice.

## United States

- **ADA Title III** (businesses open to the public): no statement is legally required, but
  courts and settlements commonly reference WCAG 2.x AA; a statement with a working
  contact channel is common practice.
- **ADA Title II** (state and local governments): the DOJ rule published in 2024
  references WCAG 2.1 AA, with compliance dates starting in 2026 depending on population
  size. Check the current DOJ guidance for dates.
  <https://www.ada.gov/resources/2024-03-08-web-rule/>
- **Section 508** (federal agencies and their procurement): references WCAG 2.0 AA via the
  Revised 508 Standards; vendors supply a VPAT/ACR.
  <https://www.section508.gov/>

## Other places

Canada (Accessible Canada Act; Ontario AODA: WCAG 2.0 AA), Australia (Disability
Discrimination Act; government: WCAG 2.1/2.2 AA), and many others reference WCAG. When in
doubt, WCAG 2.2 AA is the safest target and the statement format in this skill covers the
common elements.

## Statement quality checklist

- [ ] Conformance claim matches the evidence (automated plus manual testing on
      representative pages, with dates)
- [ ] Every known limitation says what is affected, the impact, a workaround or alternative,
      and a fix date or reason
- [ ] At least one accessible contact channel, with a response time that is actually met
- [ ] Enforcement procedure included where the regime requires it
- [ ] Linked from every page (footer), at a stable URL, in the site's language
- [ ] Review date set; updated after redesigns and audits
- [ ] No overlay or widget is presented as making the site compliant
