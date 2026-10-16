# AI Job Finder 3.1.27

## Audit of v3.1.26 export (20261016T214938Z)

426 records, 426 unique job URLs. Workplace: 313 unspecified, 66 hybrid,
44 on-site, 3 remote. Description provenance: 279 provider posting details,
115 RSS summaries, 25 unverified RSS text, 7 official full bulletins.
All 426 employer identity labels say the hiring identity is not independently
verified. Provider detail is not proof of completeness or employer legitimacy.
The export is ordered by descending comparative fit index.

Title categories: 62 executive/multi-site, 52 director, 169 manager,
65 related leadership/other, 78 supervisor/specialist. The previous specific
career filters omitted all 65 tier-2 titles: neither Management nor Other
accepted them. This release includes them under Management / related roles.
Title-based categories remain review aids, not evidence of eligibility.

## Search corrections

- Exhaustive career review categories: every title belongs to one specific filter.
- Detailed-description filter and Dashboard metric share a positive provenance
  check. Missing/unknown provenance no longer counts as detailed. RSS summaries
  and unverified RSS text remain excluded by the optional detailed-only filter.
- Underlying results and fit order are preserved. No workplace evidence invented.

## Tracker workflow

- Dashboard reminders can be marked complete, clearing the due date and using
  the existing persistence path. Status and notes remain intact; users can set
  a new date in Job Tracker. Session-only storage still requires a backup.
- Due actions include overdue items through seven days ahead, exclude closed
  statuses, tolerate invalid legacy dates, and preserve row identity for
  duplicate employer/title entries.
- Status editing has a per-row widget key, preventing a prior selection's
  status from leaking into another tracked application.

## Validation

Full root unittest discovery plus separate tests/ discovery; new coverage for
career category partition, known/unknown description provenance, due-window
boundaries, closed statuses, duplicate-title completion and backup roundtrip.
Streamlit interaction tests exercise populated review filters and reminder
completion. All six navigation pages also passed an offline AppTest smoke.
Legacy tests were brought in line with already-shipped branding, symmetric
margins, follow-up schema, full-results default and ranking-helper dependencies.
No CSS or theme changes. Live deployment and live Postgres writes not tested.
