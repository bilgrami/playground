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
