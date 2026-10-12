# Employer background checks

This feature is deliberately **on-demand**: Find Jobs → choose an opening → **Check employer**. No paid APIs or bulk business scraping. The employer check is cached for four hours and does not slow the full job search.

## What it actually verifies

- **Who supplied the job posting:** It displays the employer claimed by the feed and the source platform. For a small allowlist of career platforms and the Mayo domain, it makes a bounded HTTPS request to check whether the URL responds. This is not proof of employer identity or that the position is still open.
- **Legal identity:** Attempts an exact-name lookup in the free [GLEIF legal entity register](https://www.gleif.org/en/lei-data/gleif-api/). Ambiguous and missing results stay unknown. An LEI does not verify the person who submitted an advert.
- **Years in business:** Shows a creation date only when supplied by a matching GLEIF record, or a separately sourced historical date maintained in `employer_profiles.json`. Mayo Clinic's 1864 date describes the origins of the medical practice, **not** today's legal entity's incorporation.
- **Financial disclosures:** For exact-name listed U.S. filers, optional free SEC EDGAR annual XBRL facts can show revenue, net income, operating cash flow, assets, liabilities, and cash where disclosed. The figures are historical and are **not a credit rating, a solvency assessment, or proof that a parent guarantees a subsidiary**.
- **Private businesses, nonprofits and public agencies:** The app does not invent financial statements. It offers source-specific explanations and curated links to IRS Form 990, official audits, or government budgets.

## Optional free SEC data setting

SEC asks automated callers to identify themselves. To allow the app to retrieve SEC financial figures:

1. In Streamlit Cloud → your app → **Settings → Secrets**, add `SEC_CONTACT_EMAIL = "your-contact-email@example.com"` using an address you're comfortable providing to SEC.
2. Save the secret, redeploy, and click **Check employer** on a posting.
3. No SEC API key and **no money** are required. If you skip this setting, the app continues to check job-link and GLEIF identity evidence; SEC data stays labeled **Not checked**.

A SEC company is included only after an *unambiguous exact legal-name match*. Parent and similarly named corporations aren't silently substituted. SEC API requests are performed only on demand and cached. SEC data does not cover every private employer.

## Maintaining verified organization history

Only add an entry in `employer_profiles.json` if you have a trustworthy source. Specify:

```json
{
  "name": "Example Employer",
  "employer_type": "nonprofit",
  "history": {
    "year": 1990,
    "meaning": "Start of a documented predecessor operation, not incorporation",
    "source_url": "https://example.org/history"
  },
  "references": [
    {"title": "Audited annual report", "url": "https://example.org/annual-report"}
  ]
}
```

These are placeholders only, not a real company. Keeping employer history separate from `app.py` ensures later updates don't require changing the main program.

## Limitations

- Reachable job URLs can still point to expired or impersonated postings.
- Many legitimate businesses have no LEI; a missing match is not evidence of fraud.
- A company's age or recent profitability is not proof of its present or future financial stability.
- For government positions, review agency budgets/appropriations rather than corporate earnings.
- Employer financial evidence is a **research aid**, not a hiring guarantee, credit rating, securities recommendation, or automated screening decision.
- Some providers may block Streamlit requests. The app reports that it couldn't check rather than claiming a positive or negative result.

Relevant public sources: [GLEIF](https://www.gleif.org/en/lei-data/gleif-api/), [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [IRS tax-exempt search](https://www.irs.gov/charities-non-profits/search-for-tax-exempt-organizations), and [Mayo Clinic history](https://history.mayoclinic.org/timelines/this-month-in-our-history/).
