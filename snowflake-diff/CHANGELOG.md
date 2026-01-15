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
