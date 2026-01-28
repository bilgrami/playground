Below is an organized checklist of tasks for each role, mapped to priority, acceptance criteria and benefits.  Each milestone should conclude with a **unit‑test run (`make test`) and an updated `CHANGELOG.md` entry** to document what changed and why.  Tasks are prioritized so the most critical work (bringing the tool to a working state) happens first.

### Project Manager / Facilitator

| Task                                                                                                                     | Priority | Acceptance Criteria                                                            | Benefit                                                                    |
| ------------------------------------------------------------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| Define overall milestones and timeline based on product requirements                                                     | High     | Clear milestone plan communicated to all roles; priorities aligned with PRD.   | Ensures focused effort on core goals (reliable CLI diff, audit artifacts). |
| Coordinate hand‑offs between developers, testers and other roles; enforce post‑milestone test runs and changelog updates | High     | Evidence of regular unit‑test runs and changelog entries after each milestone. | Maintains visibility of progress and prevents regressions.                 |
| Track non‑goals (no full data reconciliation or live monitoring)                                                         | Medium   | Requirements document shows which requests are out of scope.                   | Prevents scope creep and wasted effort.                                    |

### DevOps / Environment Engineer

| Task                                                                                                 | Priority | Acceptance Criteria                                                                          | Benefit                                                                                               |
| ---------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Provision Python 3.10+ environment and install dependencies                                          | High     | `python3 --version` shows ≥3.10, `pip install -r requirements.txt` runs without errors.      | Provides a compatible runtime for all team members.                                                   |
| Ensure SnowCLI is installed and `snow` executable works; set up connection profiles for dev and prod | High     | `snow sql --connection <name> --query "select 1"` executes successfully on both connections. | Allows developers to run `make connect-test` and collect snapshots without manual Snowflake commands. |
| Configure CI (e.g., GitHub Actions) to run `make test` and publish coverage/test badges              | Medium   | CI pipeline executes tests and fails on coverage below threshold; badge endpoints update.    | Provides continuous feedback and visible health metrics.                                              |

### Backend Python Developer

| Task                                                                                                          | Priority | Acceptance Criteria                                                                                        | Benefit                                                  |
| ------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Fix unsafe SQL alias in `q_data_fingerprint()` by using a safe alias and quoting identifiers                  | High     | Diff runs on tables with special characters without SQL errors; relevant unit test added/passing.          | Prevents runtime failures when hashing data.             |
| Improve `filter_tables()` to support case‑insensitive patterns or clarify behavior; add tests                 | High     | Unit tests for LIKE/regex patterns pass; table filters work as documented.                                 | Users get predictable filtering of tables.               |
| Harden `run_sql()` to handle missing `snow` executable and timeouts gracefully                                | High     | On missing SnowCLI, the tool exits with a clear message instead of crashing; covered by tests.             | Better developer experience and quicker troubleshooting. |
| Add cleanup/overwrite logic for diff files to avoid stale diffs                                               | Medium   | Running `make diff` twice produces only current diffs; no leftover files remain.                           | Prevents confusion from obsolete results.                |
| Improve config parsing and CLI overrides (error messages for missing keys, support for environment variables) | Medium   | Invalid configs raise human‑readable errors; CLI overrides replace config values; tests cover these paths. | Reduces support effort and misconfiguration.             |

### Test Engineer / QA

| Task                                                                                                                                            | Priority | Acceptance Criteria                                                                                | Benefit                                                  |
| ----------------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Expand unit tests beyond pure helpers to cover collectors and CLI parsing                                                                       | High     | New tests mock `run_sql()` to simulate SnowCLI responses and verify table/procedure list handling. | Catches regressions in core logic and improves coverage. |
| Write tests for snapshot parsing functions (`parse_show_reduced()`, `parse_desc_reduced()`), pattern matching helpers and config override logic | High     | Tests fail when these functions misbehave; coverage improves beyond 67 %.                          | Strengthens reliability of untested areas.               |
| Define acceptance tests to run `make connect-test` and `make diff` using mocks or a sandbox database; verify expected output structure          | Medium   | Tests create `out/diffs`, `out/SUMMARY.md` and `out/snapshots` directories with correct files.     | Ensures the end‑to‑end user flow works.                  |

### Snowflake & SQL Specialist

| Task                                                                                                                               | Priority | Acceptance Criteria                                                                | Benefit                                              |
| ---------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------- |
| Review and validate SQL queries used for listing tables, procedures and computing fingerprints; adjust for quoting and performance | High     | Queries run successfully against representative schemas; documented justification. | Prevents subtle SQL errors and improves performance. |
| Advise on privileges needed for `ACCOUNT_USAGE` vs `DESC TABLE` comment modes; update config defaults accordingly                  | Medium   | README lists required grants; tool fails gracefully when privileges are missing.   | Reduces surprises for users.                         |
| Suggest optional enhancements like using object tags (DEPLOYED_AT, GIT_SHA) for more accurate change tracking                      | Low      | Enhancement logged as backlog item with rough implementation plan.                 | Future‑proofs the tool for deployment tracking.      |

### Documentation Writer

| Task                                                                                     | Priority | Acceptance Criteria                                                                                                              | Benefit                                                      |
| ---------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Update README quick‑start instructions and developer notes to reflect fixed behaviour    | High     | README shows correct install, connect‑test and diff usage; outdated notes removed.                                               | New contributors can get the tool running quickly.           |
| Document new test coverage areas and explain why collectors are now tested               | Medium   | TDD section updated to reflect expanded scope and coverage target; cross‑referenced with CI badges.                              | Clarifies testing expectations and encourages contributions. |
| Maintain and format `CHANGELOG.md` according to established template for every milestone | High     | Each changelog entry includes summary, files changed, rationale, behaviour implications, testing recommendations and follow‑ups. | Provides a clear audit trail of changes.                     |

### Security Reviewer

| Task                                                                                                          | Priority | Acceptance Criteria                                           | Benefit                                           |
| ------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------- | ------------------------------------------------- |
| Audit configuration handling to ensure that `config.yml` never stores credentials, only SnowCLI profile names | High     | Code reviewed and documented; explicit warning in README.     | Minimizes risk of accidental credential exposure. |
| Confirm that error messages and logs do not leak sensitive information; implement sanitization if needed      | Medium   | Simulated errors show no secrets; tests added.                | Protects user data and meets compliance.          |
| Review build and CI scripts for secrets management, e.g. GitHub Actions secrets                               | Low      | Workflow files use encrypted secrets; secrets are not echoed. | Maintains secure automation pipeline.             |

---

**After each milestone** (e.g., completing a set of tasks for a role), the team should:

1. **Run the full unit‑test suite** (`make test`) to verify nothing is broken and that coverage remains above the target.
2. **Create a new entry in `CHANGELOG.md`** summarizing the changes, rationale and testing recommendations.  This practice ensures transparency and helps other stakeholders track progress.

By following this structured checklist, each role knows what to prioritize, how success will be measured, and what value their work delivers toward making **snowflake‑diff** a reliable drift‑detection tool.
