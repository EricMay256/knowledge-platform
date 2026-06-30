# Test suite — Stage A

Run from the repo root:

```bash
pip install -r vault_contrib/requirements.txt pytest
pytest
```

Requires `git` on PATH (the store tests drive a real git working directory).

## Layout
| File | Covers | Notes |
|---|---|---|
| `conftest.py` | shared fixtures: `tmp` git vault, `Note` factory, `StubDeduper` | — |
| `test_decide.py` | `core.decide()` — the full policy ladder | **B2 guard** — bands are dormant in A but must be correct for B2. Do not delete as "dead-code tests." |
| `test_policy.py` | `Policy.__post_init__` ordering / range rules | **B2 guard** |
| `test_validate.py` | `core.validate()` | — |
| `test_dedup_string.py` | `_normalize()` + exact/fuzzy `find_similar` | — |
| `test_store_git.py` | `GitMarkdownStore` round-trip, review shape, commits | incl. the `---` horizontal-rule `maxsplit=2` guard |
| `test_service.py` | `ContributionService` outcomes + idempotency | — |
| `test_cli.py` | CLI status JSON + exit-code contract | agents branch on these |
| `test_idempotency.py` | client-supplied run-id replay (no-op on retry) | schema field added in Stage 1 |
