# Feature Map

This file records current user-visible behavior, not development history. Stable IDs let tests, Goals, reviews, and the temporary change guard refer to the same accepted capability.

## Feature Inventory

| ID | User capability | Entry points / connected path | Expected result | Verification | Criticality | Status |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Not yet confirmed | Identify the UI/API/background path during onboarding. | Define the first complete user journey. | Not yet confirmed | critical | planned |

## Cross-Cutting Rules

- Existing accepted behavior must not disappear unless the current Goal explicitly changes it.
- Record every connected part needed for the capability to work, such as UI control, saved setting, API, worker, persistence, and error path.
- `critical` means a small set of journeys that must be rechecked whenever source behavior changes. Use `standard` for other active capabilities.
- Use `active`, `accepted`, `stable`, or `verified` for behavior that currently exists. Use `planned` only for work that does not exist yet.
- Record important error, empty, permission, data-preservation, and compatibility behavior with the related feature.
- Every active feature must include a machine-readable verification marker in its Verification cell, such as `test:tests/export.test.js` or `suite:unit`, plus any human explanation. The change guard rejects feature-bound inline/no-op commands and commands that are not bound to the declared marker.

## Scaling This File

Keep this file as a concise index. When it becomes difficult to scan, split stable domains into `docs/features/<domain>.md` and link them here. Do not append task logs or implementation notes.
