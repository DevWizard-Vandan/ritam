# Task 009 — Full Test Suite (Jules Managed)
**Assigned to:** Jules
**Status:** TODO
**Phase:** Ongoing
**Depends on:** Tasks 001–008

## Goal
Jules maintains the full test suite:
- Write integration tests for the full pipeline:
  data → sentiment → agents → prediction → feedback loop
- Ensure 80%+ code coverage across all src/ modules
- Fix failing tests automatically when CI detects breakage
- Open a PR for each batch of test additions

## Rules for Jules
- Never modify production code in src/
- Only write or modify files in tests/
- Always run `pytest tests/ --cov=src` and include coverage report in PR description
- PR title format: "tests: add coverage for {module_name}"

## Definition of Done (Ongoing)
- [ ] Coverage > 80% across all modules
- [ ] All integration tests pass on main branch
- [ ] CI/CD pipeline runs tests on every PR

