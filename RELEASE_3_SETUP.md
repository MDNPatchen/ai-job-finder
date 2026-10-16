# AI Job Finder 3.0 — full workflow release

## Version 3.1.15 — real Mayo titles, specialist manufacturing buying, no green borders

An audit of the live v3.1.14 ranked CSV found two Mayo Clinic postings
both incorrectly titled "Breakthrough". This was the marketing heading
on a Mayo detail page, not a job name. The official job URLs identify
separate delivery management and information-security management roles.
Mayo title parsing now uses a matching actual role heading if available,
a clean employer search-result label, or the official posting URL role
slug as fallback. Title validation is specific to each vacancy URL,
rather than accepting the first h1 or a marketing slogan.

Industrial Electric Manufacturing's Purchasing Supervisor was ranked 95
while the employer explicitly requires at least three years of purchasing
or buying experience **in a manufacturing environment**. General
newspaper supplier negotiations and broad P&L experience alone do not
verify that separate professional background. A targeted 24-point
posting qualification caution now applies absent documented
manufacturing procurement, buying or purchasing work. Specific resume
evidence of that field clears the caution, and preferred-only
experience or non-manufacturing purchasing does not trigger it.

The user also requested zero green borders around the app interface.
Panels, form wrappers, metrics, expanders, navigation and module headings
now have no accent outlines; separate white modules use gutters and
quiet neutral shadows. Filled forest-green tabs and download/primary
buttons retain clear white lettering. Existing native CSV/JSON export
fragments, top navigation and employer/source coverage are preserved.

The matching engine and downloadable result filenames change to v3.1.15.
The score remains a research fit index, never an eligibility guarantee.
A fresh post-deployment nationwide search is needed to confirm actual
live posting changes.


## Modular layout and explicit remote-title repair (matching 3.1.14)

The October 16 ranked v3.1.13 CSV from a real download was parsed:
431 unique vacancy records, 38 fields, 431 nonblank application links,
with no duplicate URLs. Construction qualification handling showed the
intended Red Bull, ARCO/Murray, S&B USA and Broward improvements.
However its top-ranked non-Mayo vacancy said "(Remote)" in its title
while the provider's work arrangement metadata said "Not specified".

- Repair fully-remote text explicitly present in a vacancy title, even
  if provider work style is absent, so non-Mayo remote-only positions
  cannot bypass the existing preference filter. Mayo Clinic remains
  the sole allowed fully remote source. Ambiguous words like Remote
  Sensing are NOT treated as remote-only work arrangements.
- Replace the round-corner, continuous-card look with deliberately
  separated rectangular modules, white surfaces, slightly stronger
  section rules, generous interior padding and square metadata tags.
  Break Find Jobs into Search filters, Search overview, export files and
  Job listings, with consistent spacing.
- Top navigation no longer sits in one large rounded capsule. Each
  section has its own simple rectangular tab; the active forest-green
  tab has white text.
- Enforce true white foreground on all dark-green primary, download
  and navigation control descendants, including Streamlit paragraph
  elements which previously inherited dark text.
- Preserve the working native download fragments and UTF-8 BOM CSV
  format. The prior exported file contained all expected columns and
  valid rows. A real browser download remains user-verifiable.
- No new job providers, fake data or scoring penalties. The matching
  version moves to 3.1.14 because title-based remote filtering has
  changed, requiring a new nationwide search and versioned export.


## October 16 interface refresh — top navigation and working exports

This is a presentation and download-only update. The matching engine,
posting qualification checks, search sources, verified publisher experience,
Mayo-only remote exception, 45-day cutoff and ranked v3113 exports stay
unchanged. No fabricated job data or decorative AI imagery was introduced.

- Replaced the heavy charcoal background with a comfortable light,
  warm-neutral layout: clean white panels, forest green accents, ample
  text padding, readable form labels, stronger control contrast and
  responsive page gutters.
- Replaced the collapsible left sidebar with a horizontal navigation
  strip at the top: Dashboard, Find Jobs, Job Tracker, My Resume,
  Career Analysis, Career Matches.
- Every completed search now displays native CSV/JSON download buttons,
  regardless of whether the user uploaded a resume. Without a resume
  the file contains jobs and links; detailed qualifications require a CV.
- Wrapped download buttons in Streamlit 1.41-compatible fragment
  functions. Downloads should not trigger a full script rerun that
  could alter the selected tab or search pagination.
- Data remains in original CSV/JSON/TXT format. CSV uses UTF-8 with
  BOM for spreadsheet interoperability. Tracker backup JSON/CSV,
  Career Matches CSV and approved resume wording share this behavior.
- Smoke checks exercise all top navigation tabs and a populated
  no-resume search where export buttons must be visible. Unit tests
  verify CSV/JSON data and source preservation.

UI updates do not change comparative fit calculations, so the matching
engine version stays 3.1.13.


## Version 3.1.13 — explicit construction work minimums and required degrees

The v3.1.12 export revealed four precision regressions:
Red Bull's "5+ years of work in Construction Project Management",
S&B USA's "10+ years in preconstruction", and two ARCO/Murray
"2–5 years of construction management experience required" vacancies
were not receiving field-work cautions. ARCO's separate *preferred*
design/build experience had incorrectly overridden the earlier mandatory
criterion. Broward County's "Requires a Bachelor's degree" was still
labeled as a mention rather than as required technical education.

- Treat explicit stated years of professional construction work as a
  requirement even without the exact word "experience" (e.g. years of
  *work in* a specialist domain, and *years in preconstruction*).
- Keep distinct required-versus-preferred clauses separate within one
  combined bullet. A later preferred specialty does not erase an
  explicitly required earlier construction experience criterion.
- Recognize the narrow pre-degree "Requires a Bachelor's..." and
  "Must have a Bachelor's..." formulations as mandatory education;
  continue to honor explicitly preferred degrees and stated equivalent-
  experience substitutions.
- Keep degree-only construction requirements distinct from actual
  professional construction experience. Employer-approved bachelor's
  or associate-degree pathways remain noncumulative.
- Fifteen no-network synthetic regression cases reflect the precise
  v3.1.12 exported examples and cover required, preferred, alternative
  and misleading duty-language scenarios.
- v3.1.13 scoring and _v3113_ exports; no changes to sources, tracking
  or the approved charcoal/emerald interface.

A comparative fit index is not a hiring probability. Employer minimum
qualifications should be independently confirmed before application.


## Version 3.1.12 — professional experience vs. degree routes

The v3.1.11 ranked export identified construction degree paragraphs
being scored as independent professional construction experience,
and alternate Bachelor's/Associate's qualification routes being
penalized cumulatively.

- A construction work-experience deduction now requires actual
  qualification text about professional experience or work history.
  A bachelor's degree *in construction management* is education,
  not evidence of a required number of years in construction.
  A degree *or equivalent experience* remains an educational
  alternative, not a second experience minimum.
- Bona fide separately stated construction years and skills stay
  reviewable and penalized as appropriate, as does a required
  engineering/construction degree when evidence is absent.
- Bachelor's and Associate's minimum degree paths explicitly
  connected by an employer's "Or," wording are grouped. The
  applicant only needs one permitted route; the matching index
  applies the least severe route penalty once rather than summing
  both. Both original requirements and any pathway-specific years
  still appear in the evidence export and require verification.
- Preferred Master's qualifications and genuinely cumulative
  degrees/licenses do **not** silently become alternatives.
- Synthetic regressions based on Broward County Capital Program
  Administrator, Dexterra Facility Project Manager, LV Petroleum
  Construction Project Manager and Mayo Project Manager II–Facilities
  protect these distinctions without inventing résumé credentials.
- Only scoring, versioned exports and requirement descriptions change.
  The approved minimalist charcoal/emerald UI and search sources
  remain untouched. Matching version 3.1.12 / export _v3112_.

The score is for comparative career research, not hiring eligibility.
Missing résumé wording does not prove a user lacks a qualification.


## Version 3.1.11 — count overlapping specialist experience only once

The October 16 v3.1.10 export showed industry-specialist positions at
0/96 despite substantial, documented transferable operations experience.
For construction-management roles, essentially the same lack of field-specific
experience triggered a generic industry penalty, an additional specialized
title penalty, and a third explicit employer-experience penalty.

- The strongest caution in an explicitly mapped professional-experience
  family wins; matching domain/title/posting cues are still shown for review
  but no longer deducted three times. Categories are conservative and
  explicit—not fuzzy substring matches. Different industries and distinct
  requirements continue to score independently.
- Mandatory professional *degrees*, occupational licenses, residency and
  internal-only application rules stay separate from required industry
  *experience*. For example, the construction posting keeps its 25-point
  experience caution and separate 22-point bachelor's-in-construction-
  management/engineering caution; only the duplicate generic/title experience
  deductions are removed.
- A job with no documented transferable evidence can still have index zero,
  and a missing mandatory degree cannot produce a score above 89. There is
  no artificial global score floor and no implication that the employer would
  waive a degree or years-of-field-experience condition.
- A special clean-match bonus must *not* become available just because a
  specialist penalty moves from the generic domain layer into the employer-
  requirements layer.
- CSV and JSON record applied caution points and an additional column
  "Overlapping specialist deductions avoided (points)". In the minimal
  interface a short explanation is visible only inside the optional
  Match details expander.
- This changes the matching engine to v3.1.11 and downloads to _v3111_.
  The approved charcoal/emerald layout, search providers and remote
  employer exceptions do not change.

Synthetic regressions check Senior Capital Project Manager, Senior
Construction Project Manager, Manager Corporate Finance, unrelated senior
operations roles, separate formal credentials, and genuine zero-evidence jobs.
The next live ranking export remains necessary to measure empirical effects.


## Version 3.1.10 — construction degree rigor, finance expertise and Lever feeds

- Treat a required degree in Construction Management, Engineering, Architecture
  or equivalent technical fields as distinct from a generic Business
  Management degree. The phrase "related discipline" does not silently turn
  a management degree into a construction or engineering credential.
  Explicit employer alternatives such as Business Administration or Operations
  Management remain valid for review. Genuine required degrees are still
  verification cautions, never categorical eligibility decisions.
- Distinguish role-specific corporate-finance/FP&A skills, preconstruction
  and construction-project experience from broadly transferable P&L,
  budgets, operations and vendor management. Use both job-specific applicant
  criteria and narrow title-level cautions; ordinary leadership roles remain
  searchable and attractive.
- Paginate the free official Lever Postings API with documented skip/limit
  parameters, at most 300 vacancies per board in three 100-record pages.
  Capture individual board returned-postings, US and recently posted counts,
  pages retrieved, empty/error conditions, and partial page failures.
  Keep the valid first page when a later page fails; report an unavailable
  board separately from one that returned zero listings.
- Source audit is under the existing optional Source coverage and diagnostics
  section, without adding clutter to the approved minimal dark-emerald UI.
- Adds focused offline regression tests for v3.1.9 real-export errors, Lever
  pagination, pagination partial failures and protected cross-industry matches.
- Matching engine v3.1.10 and exports _v3110_; cached stale rankings reset.

The score is a comparative research index, not a hiring probability. Lever
API availability and vacancy freshness can still vary, and only an actual
post-search CSV can confirm how the new ranking performs in live feeds.


## Version 3.1.9 — government source integrity and degree verification

The October 16 v3.1.8 ranked export included duplicate, incorrectly
attributed NEOGOV vacancies. A City of Boise accounts-payable and
accounts-receivable requisition appeared under Charlotte County (FL) and
City of Boston (MA), because some government RSS endpoints return the
same vacancies regardless of the requested agency.

- An NEOGOV vacancy must contain the exact configured agency slug in a
  verified HTTPS governmentjobs.com/careers/<slug>/jobs/<id> URL.
  NEOED school vacancies use equivalent schooljobs.com paths.
  Cross-agency, generic, or unverified URLs are skipped, never
  mislabeled as belonging to the configured hiring agency.
- Older cached records are independently revalidated before matching.
  Duplicate verified government vacancy URLs are removed regardless
  of the feed that supplied them. Distinct requisition IDs stay separate.
- The degree classifier examines the entire individual degree clause
  instead of stopping 115 characters after the title. Thus a long
  "Bachelor's in Engineering, Operations, Business, Industrial Technology
  or related field is preferred" correctly has zero mandatory-degree
  penalty. Explicit degree requirements remain reviewable, including
  BRPH's inline EDUCATION and/or EXPERIENCE section.
- Preserve real business/management degree alternatives if a posting
  expressly permits either business or engineering education.
- Retain the premium, uncluttered dark-emerald UI from version 3.1.8.
  Version identifiers and exports now use 3.1.9 / _v319_.

This change prioritizes accuracy over count: noncanonical agency listings
may disappear until independently verified. Absence of a degree in the
uploaded resume is not proof of ineligibility, and the 0–96 score is not
a hiring probability.


## Version 3.1.8 — minimal interface and exported-results refinements

The redesigned application has a restrained charcoal/forest-emerald theme,
responsive spacing, text-only geometric branding (NO generated pictures,
briefcase illustrations, clip art or stock imagery), and real Streamlit controls.

- Keep navigation, résumé upload, nationwide search, filtering, 45-day
  listings, direct-employer screening, on-site/hybrid preferences and
  Mayo-only remote exception intact.
- Simplify visible search copy, form labels, KPI tiles, job result cards and
  action buttons. Display true job counts, employer/location, source category,
  work arrangement and relative fit **index out of 96**, not invented scores
  or a probability of getting hired.
- Place employer background checks, qualifications and provenance evidence
  behind optional expanders instead of verbose repeating paragraphs.
  CSV/JSON detailed exports remain available.
- Correct three specific edge cases from the v3.1.7 ranked CSV:
  "reside in or relocate to" is a valid relocation alternative for Hennepin
  County, an inline "EDUCATION and/or EXPERIENCE" heading can make BRPH's
  required engineering/architecture degree mandatory, and demonstrated
  5–8 years scaling social media channels is more than casual SEO familiarity.
- Retain specialist and formal qualification safeguards without excluding
  career transitions based on missing résumé words alone. Preserve previous
  technical tests and add separate aesthetic/safe-output and export-regression
  test suites.
- Matching engine **3.1.8**, exports **_v318_**; existing in-session
  prior-version rankings are cleared.

The provided static design mockup is a direction, not a screenshot of live
search results: all metrics and listings in the actual app use fetched data.


## Version 3.1.7 — requirements, relocation and degree calibration

The v3.1.6 export identified three specific issues. These changes preserve
existing nationwide coverage, free employer feeds, on-site/hybrid defaults,
Mayo Clinic remote exception, 45-day listing age and transferable matches.

- **Social-media experience**: distinguish familiarity with SEO, social media
  or digital trends from hands-on responsibility for social-media campaigns,
  channel strategy, or paid-social management. An SEO/editorial testing role
  should not get a 20-point specialist penalty just for basic familiarity.
  Dedicated social-media management roles and demonstrable campaign duties
  retain their specialist cautions.
- **Residency and relocation**: display the actual local-residency
  requirement but do not deduct comparative fit points when the employer
  expressly permits relocation to meet it. Requirements without an explicit
  relocation path remain cautioned. No assumption is made about where the
  applicant lives or willingness to relocate.
- **Mandatory professional education**: inspect job-specific advertised
  bachelor/master/doctoral degrees and regulated professional architect/
  engineering licenses before assigning 90+ fit indices. Master's-level
  business/health administration requirements for Mayo MCL Operations and
  architecture/engineering educational requirements for federal project
  executives are examples. The app distinguishes **required** from
  **preferred**, and explicitly allowed equivalent work experience from a
  strictly required degree. Absence of résumé evidence leads to a review
  caution and bounded ranking, not an eligibility rejection.
- Add exact requirement excerpts and résumé-evidence statuses to the existing
  job breakdown and CSV/JSON exports; do not claim an active credential.
  Comprehensive synthetic regression tests cover the false-positive and
  true-positive cases.
- Ranking version is **3.1.7**; stale session rankings are cleared and
  new downloads contain **_v317_**.

A résumé is an imperfect record, so these results are only comparative
career-research scores. They are not hiring probabilities or determinations
of degree, license, or residency eligibility.


## Version 3.1.6 — targeted equity-grants and specialist-career corrections

Version 3.1.5 correctly removed many compensation false positives but its
October 15 ranked export still penalized **four CLEAR customer-success and
product-management jobs** for a sentence promising future **refresh equity
grants**. These grants are part of employee compensation, not experience
administering equity plans. The app now separates receiving grants from
managing equity-compensation programs and preserves the genuine specialist
requirements of a compensation manager.

Additional fixes:

- **Hennepin County** posting titles such as
  *Classification Analyst (Internal HC applicants only)* are now flagged as
  restricted applications, without assuming the applicant is ineligible.
- **Senior social-media management** and **music rights/clearances** now
  receive specialist experience cautions if the résumé lacks those
  field-specific competencies. The job-description parser separately flags
  mandatory social-media campaigns and music-licensing background when
  present in employer applicant qualifications.
- **Event marketing** gets a modest title-grounded experience caution only
  if not substantiated; community and general marketing leadership are
  otherwise transferable.
- **Logistics coordinators** and **administrative specialists** receive
  a career-level review caution where the résumé demonstrates sustained
  senior management; not when the applicant is early-career. Manager/director
  level procurement, logistics, operations and partnerships remain included.
- Regression tests cover all four CLEAR grant cases, abbreviated
  internal-only agency eligibility, field-specific experience, and protection
  for legitimate transferable opportunities.

All roles remain visible unless excluded by the existing user-requested
location, work arrangement, age, employer and eligibility filters. Rankings
are comparative research aids, not probabilities of hiring or a decision
that a person cannot qualify. Version 3.1.6 resets previous ranking sessions
and produces **_v316_** CSV and JSON filenames.


## Version 3.1.5 — employer benefits vs applicant minimums (October 15, 2026)

The 3.1.4 ranked job export revealed a false positive: CLEAR and Imprint
management postings were given **22-point compensation administration
cautions** for the company's *total rewards and equity benefits offered to
employees*. These are not applicant qualifications.

Version 3.1.5:
- Recognizes explicit employer **Benefits**, **Perks**, **Total Rewards**,
  **Compensation & Benefits**, and **What We Offer** sections as employee
  benefits. Does not score specialty qualifications from these sections.
- Recognizes standalone offer language such as **We offer holistic total
  rewards** and **Competitive compensation and equity packages**, even when
  an employer omitted a Benefits heading or placed the text after its
  qualifications section.
- Preserves legitimate applicant requirements: a compensation and equity
  manager who needs relevant years of administering pay programs still gets
  a transparent specialist caution when résumé evidence is absent.
- Improves *career-level* ranking for a documented senior publishing and
  operations leadership background: sourcing specialists, talent acquisition
  and recruiting coordinators, purchasing/marketing coordinators, and
  assistant store managers are flagged for review without exclusion.
- Preserves cross-industry operations managers, vendor and partnership
  leadership, procurement managers, and legitimate logistics roles.
- Contains regression tests for CLEAR operations VP, Imprint general
  manager, EHS specialist, UX/product designer, mass-spec scientist,
  internal-transfer-only coordinator and both junior/senior résumé levels.
- Updates the matching engine, clearing old session rankings and producing
  new exports marked **_v315_**.

Flags are comparative research aids, never determinations of hiring
eligibility. Confirm current qualifications with the original employer.


## Version 3.1.4 — private-employer specialist minimums (October 15, 2026)

The v3.1.3 audit found highly specialized private-sector jobs still near the
top with **zero employer-specific or career-fit cautions**. Job descriptions
often contain escaped HTML, and flattening all whitespace erased critical
private employer qualification headings.

- Decode ATS HTML entities **before** stripping HTML. Preserve h2/h3/p/li
  section and list boundaries in up to 26,000 characters of description,
  including late applicant-criteria sections.
- Recognize **What You'll Need**, **What You're Great At**, **What We Need
  From You**, **What You'll Bring**, **Qualifications & Skills**, **Who You
  Are**, and other employer-specific sections as applicant requirements.
  **Nice to Have**, **Desired**, and **Preferred** stay nonmandatory.
- The requirements parser now evaluates all credible occurrences of a
  specialty and chooses the strongest evidence from the applicant criteria.
  An early mention of "deliver EHS training" in responsibilities will no
  longer mask later mandatory EHS experience in Qualifications.
- Add specialist cues for environmental safety, product/UX design, equity
  compensation, LC-MS/MS laboratory science, technical IT project delivery,
  and advanced marketing science. A regular operations/marketing/logistics
  management title does not trigger these field-specific cautions.
- Title-specific specialist cautions provide a separate check when listings
  omit qualifications, but applicants with explicit specialist résumé
  evidence are not penalized for that specialty.
- Recognize **TRANSFER ONLY** and similar explicitly employee-transfer-only
  job titles, with a visible applicant-eligibility caution.
- Keep all listings browseable, including cross-industry roles, and expose
  ranking cautions alongside literal posting excerpts in CSV/JSON.
- Invalidate v3.1.3 cached rankings and export **_v314_** filenames.

This is an explanatory research index, **not a hiring or license decision**.
Where employers omit detail or a résumé omits specialist experience, users
must independently verify actual qualifications.


## Version 3.1.3 — official full government bulletins (October 15, 2026)

Version 3.1.2 still ranked some public-sector positions at 96/96 because
agency RSS feeds gave abbreviated duties without detailed minimum
qualifications. Version 3.1.3 uses a bounded second-pass retrieval for up to
28 top-ranked NEOGOV/NEOED jobs with abbreviated or incomplete RSS text:

- The official vacancy-specific GovernmentJobs/SchoolJobs print bulletin is
  derived from the actual employer RSS vacancy URL; no IDs or job links are
  invented. Only allowed HTTPS governmentjobs.com/schooljobs.com hosts and
  print paths are fetched with strict time and size bounds.
- A title- and qualification-section-validated full bulletin can replace
  the summary before final ranking. Failed, blocked or incomplete retrieval
  keeps the original job with transparent **RSS summary only** provenance.
- Explicit full-bulletin **Qualifications / Minimum Qualifications** sections
  now supply mandatory field-experience cues even when a sentence doesn't
  repeat "required". **Desired / Preferred Qualifications** remain
  nonmandatory. Existing post-hire-certification, residency and
  internal-only flags remain in place.
- Summary-only government postings are capped at 82/96, and other
  unverified-depth provider RSS entries at 88/96; authentic full bulletins
  retain their evidence-based ranking. No job is automatically deleted.
- Job results, CSV and JSON exports show the description's provenance.
  Diagnostics report official full-bulletin retrievals and remaining
  summary-only government posts.

These are automated research rankings, not credential verification or a
prediction of hiring. Actual employer postings may be inaccessible to this
server, and only a bounded group of priority vacancies is enriched.
Existing employer-direct, U.S.-only, 45-day, on-site/hybrid and Mayo
exception filters remain unchanged.

This update invalidates older rankings. Look for **Matching engine v3.1.3**
and new download filenames containing **_v313_**.


## Version 3.1.2 — actual minimum qualifications (October 15, 2026)

The 3.1.1 ranked export still put water-system operators, EHS specialists,
product designers and an internal-only applicant ahead of clearly transferable
business-management roles. The v3.1.2 search adds a separate evidence-based
check of *actual requirements written in the employer posting*:

- **Application eligibility**: explicit internal-applicant-only conditions in
  the title or job text receive a large ranking caution, never an ungrounded
  assertion that the user is ineligible.
- **Mandatory field-specific experience**: job-specific wording about water
  utilities, industrial safety, product/UX design, building engineering,
  emergency management, technical accounting and instructional credentials
  counts when phrased as a minimum qualification. Generic management terms
  are not evidence of specialized qualifications.
- **Credentials and portfolios**: context such as water-operator certification,
  professional engineering credentials, OSHA requirements and design
  portfolios is flagged. "Preferred" is not treated as required; the option
  to obtain a credential after hiring is treated differently from requiring
  one at application time. Résumé mentions do not prove a license is current.
- **Residency**: an explicit local residency rule lowers priority and is
  shown for individual verification, without assuming where the user lives.
- **Conflicting workplace descriptions**: explicit *full* in-person attendance
  in the posting overrides an ATS hybrid/remote label for the job display,
  and the disagreement is highlighted. Clearly hybrid schedules with
  occasional office days are preserved.

Every detected condition has supporting employer-posting text and can be
reviewed in the job card and ranked CSV/JSON exports. The résumé provides
only limited evidence; nothing here establishes hiring eligibility or
guarantees that a vacancy is open. **All jobs remain browseable** unless
removed by existing filters. Version 3.1.2 invalidates the old 3.1.1
search session and produces export filenames containing **_v312_**.


## Version 3.1.1 — career suitability guardrails (October 15, 2026)

The 3.1.0 job export surfaced unrelated specialist and early-career openings
with near-perfect scores simply because lengthy job descriptions referenced
generic skills (budgets, managers, strategy, reporting). **Skills overlap does
not establish that a role is a good career transition.**

Version 3.1.1 adds independent, conservative career-fit cautions for:
- Job titles indicating specialized training (for example engineering,
  software/IT administration, accounting or capital-markets, clinical care,
  technical data journalism, court practice or teaching) without matching
  field-specific evidence in the uploaded résumé.
- Internships, trainees and some narrower first-line or assistant roles, but
  only when the résumé evidences substantial prior management experience.

This reduces comparative fit ranking without silently deleting positions or
claiming an applicant is formally ineligible. A résumé explicitly documenting
the specialized field bypasses that field's caution. The display shows the
reason for each caution; CSV/JSON exports preserve it too.

Cross-industry operations, logistics, partnerships, procurement, marketing
and customer-management roles remain welcome. The default source screening,
45-day limit, and Mayo Clinic remote exception are unchanged.

Run a new search after deployment. Prior 3.1.0 rankings are invalidated and
new export filenames contain **_v311_**.


## Version 3.1.0 — résumé strengths first (October 15, 2026)

This build does **not** limit your career search to newspaper, publisher or
executive titles. The default job rankings emphasize **which actual duties in
a job posting overlap with strengths evidenced by your uploaded résumé**.
Examples include managing people, budgets and P&L, operations, revenue growth,
distribution, vendor negotiation, digital work, strategy and partnerships,
when those capabilities are actually supported by your résumé.

- Documented job-duty matches provide most of the comparative score. An
  impressive or familiar job title contributes only a small component.
  Words appearing **only in the job title** no longer get full duty-overlap
  credit.
- Jobs with unconventional titles can be included when the real job
  description documents multiple relevant areas, rather than being discarded
  solely for missing a predetermined management title.
- Required specialty experience, professional licenses, civil-service rules
  and other verification needs remain explicit cautions rather than
  assumed qualifications or absolute disqualifications.
- Job cards now show the leading transferable areas, and ranked CSV/JSON
  exports include documented versus separately confirmed transfer strengths.
- Your existing U.S.-only, 45-day, direct-employer, hybrid/on-site and Mayo
  Clinic exception filters remain unchanged.
- Rankings are research indicators, **not** eligibility decisions or
  predictions of interview success. Always check the full employer posting.
- Scoring changes reset old cached rankings. Look for **Matching engine
  v3.1.0** and new ranked export filenames containing **_v310_**.


## Version 3.0.1 — employer-direct search quality (October 15, 2026)

**New default:** Find Jobs → **Listing sources** → **Direct employers only
(recommended)**. This hides listings posted by recognizable search firms,
recruiting agencies and staffing companies (including Keller Executive
Search), third-party aggregate boards, and general job directories such as
the NYC public jobs landing page when a vacancy-specific URL is unavailable.
The filtering also rejects explicitly Canadian job locations mistakenly
interpreted as California.

You can switch to **Include recruiter listings with direct job links** to
opt back into recruiting intermediaries, or **All sources (including
directory links)** to see everything. Exclusion counts appear beneath search
results. These options change source screening, not resume scoring, 45-day
age restrictions, the Mayo Clinic remote exception, or the existing state and
workplace filters.

**Important:** A named employer board and a link to a specific job do NOT
prove the job is still accepting applications or independently verify the
hiring organization. Open the vacancy on the company or agency site, and
use **Check employer** for additional on-demand evidence. NYC public data
without vacancy-specific URLs is available only in the broader search mode,
not silently represented as a direct application link.

The engine version is **3.0.1**, which deliberately invalidates in-session
rankings and labels new CSV/JSON exports so the prior 3.0.0 results do not
appear to have been filtered.


This app is **free to search**. It uses public career boards, official government
RSS feeds, and optional user-supplied USAJOBS credentials. No payment-card,
OpenAI, LinkedIn or Indeed credential is required.

## What changed

1. **Distinct vacancies:** same employer/title in different places or distinct
   official requisition URLs stay separate. True duplicates with the same
   canonical official URL are consolidated.
2. **Source health:** the Find Jobs diagnostics show **Active**, **Empty** and
   **Failed** for each configured board. "Active" means the feed supplied
   records, not that every record is still open or matches your criteria.
3. **Applications:** backup and restore prior CSVs, or export/import a full JSON
   backup including your previously seen job IDs. Save status/notes and delete
   individual applications. In-memory mode is temporary.
4. **Optional permanent storage:** connect your own private PostgreSQL instance
   using Streamlit Secrets. It is not configured by the GitHub repository and
   is never provisioned or paid for automatically. The app never writes
   application data or resumes into GitHub.
5. **Advanced filters:** include/exclude selected states, seniority categories,
   minimum **listed annual salary** and salary-unlisted preferences, and hide
   job postings where on-site/hybrid status has not been explicitly stated.
6. **What is new:** the first search creates a baseline. On later searches,
   the interface flags postings not found previously. Filter to "New only"
   and hide jobs already in the tracker. A JSON backup includes this baseline.
7. **Coverage:** added New Castle County, Delaware's verified NEOGOV career
   board. 159 employer/agency board identifiers are configured, spanning 49
   states in the government/education feed catalog. Maine's official state
   portal is **not** currently exposed as a verified compatible RSS/API feed
   and is not misrepresented as directly integrated.

## First launch

Once GitHub Actions pass and the merge appears in Streamlit, check that the
app says **Matching engine v3.0.0** and **159 configured boards**.

Upload your resume, search **All states**, **On-site + Hybrid**, with
**All matching jobs**, leave the job keyword blank and filters clear. The
new-job count is **zero on this first search** by design: it establishes the
baseline, rather than presenting hundreds of old results as new. Run again
after fresh postings are added.

Use **Job Tracker → Download complete tracker backup (JSON)** after your
first search to preserve the baseline if cloud storage is not enabled.

## How to make the tracker permanent

Streamlit session state and local disk are **not durable storage** on Community
Cloud. The app deliberately does not claim otherwise.

Use a privately owned PostgreSQL database (for example, a managed Postgres
instance you control). Enable SSL/TLS on the database server. In Streamlit
Community Cloud select **Manage app → Settings → Secrets** and configure:

    TRACKER_DATABASE_URL = "postgresql://ACCOUNT:PASSWORD@HOST:5432/DATABASE?sslmode=require"
    TRACKER_ACCESS_PASSWORD = "CHOOSE_A_UNIQUE_LONG_RANDOM_SECRET"
    TRACKER_WORKSPACE_ID = "personal-job-tracker"

The password must have at least **12 characters**. Use a strong, random value,
not the Postgres password. Never add these secrets to GitHub or a public issue.

1. Reboot the app (or let Streamlit deploy the Secrets change).
2. Open **Job Tracker**, enter your tracker access password, and select
   **Unlock saved applications**. The server creates the workspace table
   on first authenticated access.
3. After unlocking, searches, saved applications, status changes and imports
   sync to the private Postgres record for this workspace.
4. Before removing/updating the database, export a full JSON backup.

This is a **single-user, password-gated tracker**, not multi-user access
control. Protect the Streamlit app and database accordingly. The Postgres
database must grant the configured connection permission to create the
workspace table and insert/update records. Credentials stay in server-side
Secrets. If the database is unavailable, the app still permits session edits
but warns that the cloud save did not succeed. Export JSON immediately.

### No database yet?

Everything else works without a database. Use the full JSON export and
restore it in the Job Tracker on your next browser session. Legacy
**job_tracker.csv** files remain supported for application restore, but they
cannot recover the previously-seen-job history. CSV import can merge with or
replace tracked applications. Replacing a JSON backup also replaces the
seen-job history.

## Important accuracy notes

- The 45-day cutoff is still enforced. Undated jobs are excluded.
- Full remote positions are still excluded except for **Mayo Clinic**.
- A salary minimum uses the lower bound of *explicitly annual* posted dollar
  amounts; hourly and unlisted pay are not automatically converted.
- Employer/provider availability depends on third-party APIs and can change.
  An apparently active employer career page does not ensure a working feed.
- Ranking is a comparative resume-evidence research indicator, **not** a
  hiring-success probability or formal eligibility determination.
- The application does not independently verify job validity or employment.
- Data security depends on who can access your Streamlit app and PostgreSQL
  database. Back up your data before importing a replacement or resetting.
