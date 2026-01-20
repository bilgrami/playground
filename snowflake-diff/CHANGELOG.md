# CHANGELOG

All notable changes to this project will be documented in this file.

---

## Format
- **Reverse chronological order** (newest at top)
- **Header format:** `YYYY-MM-DD | <category>: <title>`
- **Categories:**
  - 🚀 **feat**
  - 🐛 **fix**
  - 📘 **docs**
  - 🧹 **chore**
- **Sections included in every entry:**
  - 📄 **Summary**
  - 📁 **Files Changed**
  - 🧠 **Rationale**
  - 🔄 **Behavior / Compatibility Implications**
  - 🧪 **Testing Recommendations**
  - 📌 **Follow‑ups**

---

## 2026-01-19 | 📘 docs: Comprehensive documentation and security updates

### 📄 Summary
- Added Architecture.md with Mermaid diagrams in collapsible sections
- Updated README with environment variable documentation, improved troubleshooting table
- Updated TDD section to reflect expanded test coverage (71 tests, 92%)
- Added security warning about credentials
- Aligned CI coverage threshold with Makefile (80%)

### 📁 Files Changed
- `Architecture.md` - New file with system diagrams, data flow, and module responsibilities
- `README.md` - Added env vars section, updated TDD, improved troubleshooting, security note
- `.github/workflows/snowflake-diff-tests.yml` - Updated coverage threshold to 80%
- `CHANGELOG.md` - This entry

### 🧠 Rationale
- Architecture documentation aids onboarding and understanding
- Security note reminds users to never commit credentials
- CI/Makefile alignment prevents configuration drift

### 🔄 Behavior / Compatibility Implications
- No runtime changes; documentation and CI only

### 🧪 Testing Recommendations
- `make test` (71 tests, 92% coverage)

### 📌 Follow‑ups
- None

---

## 2026-01-19 | 🚀 feat: Case-insensitive filtering, environment variables, and improved errors

### 📄 Summary
- Added case-insensitive pattern matching for table filtering (default, recommended for Snowflake)
- Added environment variable support for all connection config (SNOWDIFF_LEFT_*, SNOWDIFF_RIGHT_*)
- Improved error messages to suggest solutions (env var, CLI flag, or config file)
- Expanded test coverage to 92% with 71 tests

### 📁 Files Changed
- `scripts/collectors.py` - Case-insensitive matching in `filter_tables()` and `matches_pattern()`
- `scripts/snowdiff.py` - Environment variable support via `get_env_var()`, improved error messages
- `config.yml` - Added `case_sensitive` option documentation
- `tests/test_collectors.py` - Added case sensitivity tests
- `tests/test_config.py` - Added env var and error message tests
- `.coveragerc` - Updated exclusion patterns
- `Makefile` - Raised coverage threshold from 67% to 80%
- `CHANGELOG.md` - This entry

### 🧠 Rationale
- Snowflake unquoted identifiers are case-insensitive; patterns should match accordingly
- Environment variables enable container/CI/CD deployments without config file editing
- Clear error messages reduce support burden and improve developer experience

### 🔄 Behavior / Compatibility Implications
- **BREAKING**: Pattern matching is now case-insensitive by default (set `case_sensitive: true` for old behavior)
- **Config priority**: Environment vars > CLI args > config file
- Environment variables: `SNOWDIFF_<SIDE>_<FIELD>` (e.g., `SNOWDIFF_LEFT_CONNECTION`)

### 🧪 Testing Recommendations
- `make test` (71 tests, 92% coverage)
- Test env vars: `SNOWDIFF_LEFT_CONNECTION=test python scripts/snowdiff.py ...`
- Verify case-insensitive matching: pattern `fact_%` should match `FACT_SALES`

### 📌 Follow‑ups
- Add CLI flag for case sensitivity (`--case-sensitive`)

---

## 2026-01-19 | 🐛 fix: Critical bug fixes for SQL safety, timeouts, and cleanup

### 📄 Summary
- Fixed unsafe SQL alias in `q_data_fingerprint()` that caused failures on tables with special characters
- Added configurable timeout (default 300s) to `run_sql()` to prevent indefinite hangs
- Added automatic cleanup of stale diffs/snapshots before new runs
- Added comprehensive unit tests for auth and collectors modules (38 tests total, 91% coverage)

### 📁 Files Changed
- `scripts/collectors.py` - Quoted SQL identifiers in fingerprint query
- `scripts/auth.py` - Added timeout parameter with graceful error handling
- `scripts/snowdiff.py` - Added `cleanup_output_dir()` function
- `tests/test_auth.py` - New test file for auth module (6 tests)
- `tests/test_collectors.py` - New test file for collectors module (24 tests)
- `CHANGELOG.md` - This entry

### 🧠 Rationale
- Tables with spaces, special characters, or SQL reserved words caused runtime failures
- Long-running queries could hang indefinitely, blocking the tool
- Stale diff files from previous runs caused confusion and misleading audit trails

### 🔄 Behavior / Compatibility Implications
- **SQL generation**: Identifiers are now properly quoted with double quotes
- **Timeout**: Queries now timeout after 300 seconds by default (configurable)
- **Cleanup**: Running `make diff` now clears previous output before generating new results

### 🧪 Testing Recommendations
- `make test` (38 tests, 91% coverage)
- Test with table names containing spaces: `"MY TABLE"`
- Verify timeout behavior with large queries

### 📌 Follow‑ups
- Add environment variable support for timeout configuration
- Add case-insensitive pattern matching option
- Continue expanding test coverage for snowdiff.py

---

## 2026-01-14 | 🧹 chore: repo-level CI workflow for badges

### 📄 Summary
- Added a repo-root CI workflow for snowflake-diff tests and badge publishing.
- Updated README badges to point at the new workflow.

### 📁 Files Changed
- `.github/workflows/snowflake-diff-tests.yml`
- `README.md`
- `CHANGELOG.md`

### 🧠 Rationale
- Ensure the workflow runs from the repository root so badges resolve correctly.

### 🔄 Behavior / Compatibility Implications
- No runtime changes; CI only.

### 🧪 Testing Recommendations
- `make test`

### 📌 Follow‑ups
- Remove the legacy workflow under `snowflake-diff/.github/` if no longer needed.

## 2026-01-14 | 🧹 chore: dynamic badges via CI artifacts

### 📄 Summary
- Generate coverage and unit test badges from CI artifacts.
- Publish badge JSON to GitHub Pages for dynamic Shields endpoints.

### 📁 Files Changed
- `.github/workflows/tests.yml`
- `README.md`
- `CHANGELOG.md`

### 🧠 Rationale
- Keep coverage and test count badges in sync with CI results.

### 🔄 Behavior / Compatibility Implications
- Adds a GitHub Pages deploy job for badge artifacts.

### 🧪 Testing Recommendations
- `make test`

### 📌 Follow‑ups
- Enable GitHub Pages (Actions) if not already configured.

## 2026-01-14 | 📘 docs: testing + badges + dev notes

### 📄 Summary
- Added unit test docs, PRD/TDD sections, and developer setup notes.
- Added badges for CI, coverage, and unit test count.

### 📁 Files Changed
- `README.md`
- `Makefile`
- `.coveragerc`
- `.github/workflows/tests.yml`
- `requirements.txt`
- `tests/test_utils.py`
- `tests/test_diffing.py`
- `tests/test_reporting.py`
- `CHANGELOG.md`

### 🧠 Rationale
- Clarify testing expectations and ensure quick onboarding.
- Surface CI health and coverage at a glance.

### 🔄 Behavior / Compatibility Implications
- No runtime behavior changes; documentation and test tooling only.

### 🧪 Testing Recommendations
- `make test`

### 📌 Follow‑ups
- Consider adding dynamic coverage/test count badges via CI artifacts.
