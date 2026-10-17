# AI Job Finder 3.2.3

Search runs in a per-session background task. Results arrive as providers finish; navigation remains available, Stop search cancels outstanding work cooperatively, and completed results survive cancellation or a later error. Resume and verified-experience changes invalidate a running search. Previous results remain available until the new search has usable results. Partial results are labeled explicitly.

Repeated description cleanup and scoring are avoided within each search. Mayo keyword discovery runs with three workers, up to 60 discovered details are checked, and SmartRecruiters allows up to 50 pages within its existing time budget. Coverage limits remain visible. Public requests retain TLS hostname and certificate verification while supplementing host trust with the installed, pinned CA bundle.

Unavailable feeds retain failure status and detailed errors. Official career links provide a manual route for Bold Business, Duval County, Ventura Unified, and Rhode Island; these links do not count as recovered automated coverage.

Tracker JSON backups include a corruption-detection checksum. Import validates the complete payload before applying changes, clears stale editor fields, preserves existing competing records during merges, and retains a downloadable pre-restore backup. Real PostgreSQL integration tests exercise restart/reload, application and employer-evidence restoration, and version history using an isolated database.

Match review exports up to 40 jobs, with the first 20 and a spread through the remaining rankings, posting text, and resume evidence. Completed reviews are checked against the original search and resume fingerprint. Blank or uncertain judgments never become accuracy claims.

The supplied-resume review also identified and corrected missed Civil PE credentials, dotted I.T. project titles, post-hire city residency, healthcare-clinic management minimums, and a long graduate-degree substitution incorrectly treated as mandatory. Negated credential evidence cannot waive a license caution. Government summary counts now describe matching results rather than all fetched records.

Validation includes regression and evidence tests, PostgreSQL backup/recovery integration, six-page/six-width theme checks, and a deterministic browser workflow covering partial results, navigation, cancellation, retained results, and a second completed search. Forest-green styling and margins are unchanged.

Limitations: stopping waits for bounded in-flight requests to return; tasks are session-local and do not survive server restarts. Search health is a snapshot. Match reviews require user judgments. A disposable-database restore test is not a production disaster-recovery exercise.

Deployment validation exposed a slower cold start than local tests. Public JSON caching now runs independently of Streamlit, bounds cache storage to 32 MB of serialized public data, and coalesces concurrent requests for the same URL. Certificate trust initializes once under a lock. Source coverage exports include completion status, worker first-result time and elapsed time so UI delay can be distinguished from retrieval time.
