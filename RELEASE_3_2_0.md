# AI Job Finder 3.2.0 — reliability redesign

This release addresses the reliability audit through shared persistence and
recovery, evidence interpretation, source coverage, and repeatable validation.
The forest-green theme and existing content margins are retained.

## Saved work and recovery

All pages show whether changes are saved to cloud, session-only, failed, or
blocked by a newer cloud version. Failed saves retain local edits and offer a
recovery JSON download and retry. Concurrent sessions use atomic revision
checks. A three-way merge preserves independent edits and deletions; competing
edits require an explicit choice. The most recent 20 cloud versions are
available for recovery from Job Tracker.

Existing schema-1 JSON backups and the existing Postgres workspace migrate to
schema 2. Employer checks are included in cloud storage and full JSON backups.
The backup/import size allowance is consistent at 256 MB, covering the 5,000-job
limit including long Unicode notes. Seen-job history retains the most recent
25,000 IDs. CSV remains spreadsheet-safe; JSON is the exact recovery format.

Deployment adds a revision column and a recovery-history table to the existing
database. The database role needs permission for this migration. Restart the
app when deploying and refresh old tabs; pre-3.2 clients must not keep writing
the old unconditional workspace format. Download a JSON backup before rollout.
Never roll back to an old writer against the upgraded database without first
stopping writes and restoring the desired snapshot.

## Matching and source evidence

Resume evidence rejects negated, aspirational, coursework-only and explicitly
quoted job-requirement clauses. Affirmative clauses in mixed statements remain
usable. Past-tense “led teams” is recognized. These are conservative rules;
uncertain wording still needs human review. A 20-case synthetic acceptance
benchmark is included; it is not a measured real-world ranking accuracy claim.

Description review now inspects usable content, duties, qualification headings,
RSS provenance and truncation. Empty or boilerplate-only text no longer passes
as detailed just because it comes from a provider. Qualification scanners use
a consistent 26,000-character job-text boundary and truncation is disclosed.

SmartRecruiters paginates up to 10 pages and checks up to 100 relevant details
per employer, disclosing any cap or detail failure. Mayo's bounded keyword
coverage is explicitly partial. JSON requests have bounded transient retries,
response limits, and propagated request budgets. Successful JSON may be cached
for 15 minutes; aggregated failures are not cached for hours. Search and source
health displays flag incomplete coverage rather than implying a complete list.

Employer evidence persists with timestamps and is accessible from the tracker.
Checks older than 24 hours are marked stale in the search view. Explicit closed
posting text and HTTP 404/410 are distinguished from mere page accessibility.
Legal identity, page access and vacancy availability remain separate signals.

## Verification and operations

- Exact application dependencies are pinned in requirements.lock; unused OpenAI
  runtime dependency removed.
- Full regression, synthetic evidence evaluation, real Postgres concurrency,
  migration/history, and desktop/mobile browser checks run in release CI.
- Browser checks cover all six pages, version, forest-green background, symmetric
  margins and horizontal overflow; screenshots are retained as CI artifacts.
- A manual deployed-app workflow accepts a deployment URL and expected version.
- Source request handling, description quality, evidence context, synchronization,
  merge logic and SmartRecruiters retrieval are separate testable modules.

Repository branch protection is an administrative setting, not a file change.
Require the “regression” status before merging future changes. CI cannot by
itself prove that the production deployment, database credentials or every
external provider is healthy.
