# AI Job Finder 3.0 — full workflow release

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
