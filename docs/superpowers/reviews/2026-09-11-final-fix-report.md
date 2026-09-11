# Fix pass over final whole-branch review findings

Base: `9068de5` (122 tests passing). Worktree:
`D:\projects\task-and-kpi\.claude\worktrees\feat-backend-mvp`, `backend/` run
from a venv with `.venv\Scripts\Activate.ps1`.

## Finding 1 (CRITICAL) — non-finite `final_delta` corrupts the ledger

**Root cause confirmed by reproduction** (see below): `KpiApproveIn.final_delta`
had no `allow_inf_nan=False`, and `approve_kpi_suggestion` never checked
finiteness before writing to `kpi_progress_entries`.

Changes:
- `backend/app/schemas.py`: `KpiApproveIn.final_delta` now
  `Field(allow_inf_nan=False)`.
- `backend/app/services/approval.py`: `approve_kpi_suggestion` now checks
  `math.isfinite(final_delta)` right after the `final_kpi_id` `NotFoundError`
  check and before any mutation, raising `InvalidInputError` (Vietnamese
  message) — mirroring `validate_extraction_result`'s guard on the LLM side.

Tests added:
- `tests/test_api_suggestions.py::test_approving_with_infinite_delta_is_rejected`
  and `::test_approving_with_nan_delta_is_rejected` — 422 over HTTP, ledger
  still empty, suggestion still `pending`.
- `tests/test_service_approval.py::test_infinite_final_delta_raises_invalid_input`
  — direct service call with `float("inf")` raises `InvalidInputError`, no
  ledger row, suggestion stays `pending`.

## Finding 2 (IMPORTANT) — same gap, two more endpoints returning 500

Symptom 1 (approve/NaN → `IntegrityError` → 500) is fixed by the same
`allow_inf_nan=False` addition above (Pydantic now rejects it before it ever
reaches SQLAlchemy).

Symptoms 2 and 3 (`POST /api/kpis` with `NaN`/`1e400` target_value) needed:
- `backend/app/schemas.py`: `KpiCreate.target_value` and
  `KpiUpdate.target_value` both gained `allow_inf_nan=False` (kept alongside
  the existing `gt=0`).

**Surprise**: adding `allow_inf_nan=False` alone was not enough to get a clean
422. Pydantic correctly produces a `RequestValidationError` whose `errors()`
embeds the raw invalid input (e.g. `input: inf`). FastAPI's *default*
`RequestValidationError` handler then calls `jsonable_encoder` + Starlette's
`JSONResponse.render`, which does `json.dumps(..., allow_nan=False)` — and
crashes with the *exact* `ValueError: Out of range float values are not JSON
compliant` described in the finding, except now on the *error* response
itself, still a 500. This reproduced for target_value **and** for
final_delta once Pydantic rejected it up front — i.e. Finding 1's endpoint
was also affected by this handler bug, not just the two Finding 2 endpoints.

Fix: `backend/app/main.py` now registers a custom
`@app.exception_handler(RequestValidationError)` that walks
`jsonable_encoder(exc.errors())` and replaces any non-finite `float` with its
`str()` (`"inf"`, `"-inf"`, `"nan"`) before building the `JSONResponse`. This
is the only way to guarantee 422 instead of 500 whenever the invalid input
itself is a non-finite float — the crash is otherwise inherent to
FastAPI/Starlette's defaults, independent of which field triggers it.

Tests added:
- `tests/test_api_crud.py::test_infinite_target_value_is_rejected` — 422 for
  `1e400`.
- `tests/test_api_crud.py::test_nan_target_value_is_rejected_cleanly` — 422
  for `NaN`, confirming the handler no longer crashes.

## Finding 3 (IMPORTANT) — failed-extraction path had no HTTP coverage

- Renamed `tests/test_api_reports.py::test_failed_extraction_is_reported` →
  `test_empty_extraction_is_still_a_success` (body/assertions unchanged —
  it genuinely tests the empty-but-successful extraction path).
- Added `test_provider_failure_is_reported_over_http`: overrides
  `get_llm_provider` with `ScriptedProvider(error=ExtractionError("LLM
  hong"))` via `app.dependency_overrides`, submits a report, asserts 201 with
  `extraction_status == "failed"`, non-null `extraction_error`, and empty
  `kpi_suggestions`/`task_suggestions`/`blockers`. The override is removed in
  a `finally` block, the same pattern `api_client` uses.
- Added `test_failed_report_can_be_reextracted_over_http`: same setup, then
  with the override removed, `POST /api/reports/{id}/extract` succeeds (200),
  flips `extraction_status` to `"extracted"`, and clears `extraction_error`
  to `null`.
- `tests/test_service_reextraction.py::test_failed_report_can_be_reextracted`:
  added `assert report.extraction_error is not None` right after the failure
  and `assert report.extraction_error is None` after reextraction — this test
  previously only checked the status flip.

## Finding 4 (IMPORTANT) — `anthropic` floor too low for the structured-output API

- `backend/pyproject.toml`: `"anthropic>=0.40"` → `"anthropic>=1.5"`. No
  reinstall performed — the venv already has 1.5.0
  (`anthropic.__version__ == "1.5.0"`), confirmed by import.

## Spec update

`docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md` §7.4: added one
sentence (Vietnamese, matching surrounding prose) right after the
`final_kpi_id`-must-not-be-null sentence, stating `final_delta` must be a
finite number and a non-finite value is rejected with HTTP 422 with no
mutation performed.

## Commands and output

Baseline (before any change):
```
cd backend; .venv\Scripts\Activate.ps1; python -m pytest -q
122 passed, 1 warning in 4.23s
```

After all fixes + new tests, focused run:
```
python -m pytest -q tests/test_api_suggestions.py tests/test_service_approval.py tests/test_api_crud.py
41 passed, 1 warning in 1.57s

python -m pytest -q tests/test_api_reports.py tests/test_service_reextraction.py -v
17 passed, 1 warning in 1.00s
```

Full suite, final:
```
python -m pytest -q
129 passed, 1 warning in 4.66s
```
122 original + 7 new (2 in test_api_suggestions.py, 1 in
test_service_approval.py, 2 in test_api_crud.py, 2 in test_api_reports.py).
No failures, no skips. `test_service_reextraction.py` gained assertions on an
existing test rather than a new test, so it contributes 0 to that count.

## Critical reproduction, re-run after the fix

Reproduced the exact scenario from the finding using a raw-HTTP TestClient
script (`json=` can't carry `inf`/`NaN` itself — httpx's own encoder rejects
them — so the script sends a raw JSON body, matching how a real non-Python
client would send `1e400`):

```
POST /api/suggestions/kpi/{id}/approve  {"final_kpi_id": <id>, "final_delta": 1e400}
  -> HTTP 422
  {"detail":[{"type":"finite_number","loc":["body","final_delta"],"msg":"Input should be a finite number","input":"inf"}]}

POST ... {"final_delta": NaN}
  -> HTTP 422
  {"detail":[{"type":"finite_number","loc":["body","final_delta"],"msg":"Input should be a finite number","input":"nan"}]}

POST /api/kpis {"target_value": 1e400, ...}
  -> HTTP 422 (previously 201 with target_value silently becoming null)

POST /api/kpis {"target_value": NaN, ...}
  -> HTTP 422 (previously 500 — the validation-error handler itself crashed)

kpi_progress_entries after all four calls: 0 rows
suggestion status: still PENDING
```

## Concerns / things worth flagging to the reviewer

- The fix required touching `app/main.py` to add a custom
  `RequestValidationError` handler — this wasn't explicitly named as a file
  to change in the brief, but it's the only way to make the 422 (not 500)
  requirement in Findings 1 and 2 actually hold; without it, adding
  `allow_inf_nan=False` alone converts a "500 after silent corruption" bug
  into a "500 in the error handler" bug, which still isn't the spec's §9
  convention. I judged this in-scope since Finding 2 explicitly requires "a
  clean 422 body rather than crashing the error handler" as a test assertion.
- Did not touch anything else in `main.py`, and did not change the shape of
  existing error bodies for any other validation failure (they pass through
  `_sanitize_non_finite` unchanged since it's a no-op on already-finite
  values).
- Left all "carry" Minor items untouched, per instructions.
