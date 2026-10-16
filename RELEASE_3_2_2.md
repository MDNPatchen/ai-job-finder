# v3.2.2 — auditable ranking and export validation

Support roles such as Executive Assistant to the President no longer inherit the seniority of the person they support. Assistant General Manager remains management rather than executive leadership. Genuine chief executive and deputy county manager titles retain their executive classification.

CSV and JSON exports now disclose the leadership review priority, role-level adjustment and description-quality adjustment. These explain ordering without changing the comparative fit score or implying hiring probability. The forest-green layout and spacing are unchanged.

A read-only CSV validator checks required columns, complete rows, sequential ranks, duplicate URLs, posting identifiers, consistent engine/run/order metadata, finite score bounds, priority arithmetic and selected ordering. Invalid data fails; older leadership exports lacking priority details are marked unverified. This is structural validation, not independent proof of job suitability or source coverage.

Validation command: `python scripts/audit_export.py /path/to/export.csv`.

Payroll, healthcare revenue-cycle and merchant-payments roles now have field-specific checks. Generic budgeting, revenue growth and vendor payments do not establish these specialties. Title and description cautions in the same field are counted once; documented specialty evidence removes the missing-field caution. Tests cover positive evidence, negation, preferred qualifications and unrelated general operations roles.

Readiness toward 90% still requires human-reviewed relevance evaluation, source diagnostics from real searches and production recovery evidence. Automated tests alone cannot establish a reliability probability.
