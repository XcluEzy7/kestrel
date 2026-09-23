---
id: KST-9
title: Keep provider-model downgrade safe with nullable data
status: Done
assignee:
  - '@Erik'
created_date: '2026-09-23 07:22'
updated_date: '2026-09-23 07:29'
labels:
  - bug
  - migrations
dependencies: []
priority: high
type: bug
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The provider model field now permits NULL, while the new downgrade unconditionally restores NOT NULL. A database containing a NULL model cannot roll back. Make rollback safe without inventing a replacement provider model.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Downgrade handles persisted NULL provider models without an integrity error or fabricated model
- [x] #2 A non-NULL model remains intact across upgrade and downgrade
- [x] #3 Rollback policy and recovery behavior are explicit when NULL cannot be represented in the older schema
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproduce downgrade failure with a persisted NULL provider model and inspect migration/test conventions. 2. Guard the downgrade before schema alteration: fail explicitly with a recovery instruction when NULL rows exist, without fabricating models or deleting data; allow normal downgrade after valid models are supplied. 3. Extend tests/test_migrations_packaging.py to assert the failure preserves data and a non-NULL round trip succeeds. 4. Run migration tests and real SQLite upgrade/downgrade smoke.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
SQLite/Alembic reproduction failed before fix with NOT NULL IntegrityError. Downgrade now counts NULL models and raises an actionable error before schema alteration; operator supplies a genuine model and retries. Independent validation: tests/test_migrations_packaging.py 14 passed; targeted Ruff and git diff --check passed; regression asserts row/data/schema intact across failure, retry, and re-upgrade.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Guarded nullable provider-model rollback without inventing or deleting data. Reproduced and resolved the SQLite failure; 14 migration packaging tests, Ruff, and whitespace check passed.
<!-- SECTION:FINAL_SUMMARY:END -->
