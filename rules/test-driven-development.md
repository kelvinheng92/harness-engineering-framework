# Test-Driven Development

## Mandate

All new features and bug fixes must follow the Red → Green → Refactor cycle.
Write a failing test first; only then write the minimum production code to make
it pass.

---

## Workflow — REQUIRED for every change

1. **Write the test first** — create or extend a test file before touching
   production code. The test must fail for the right reason before you proceed.
2. **Write the minimum code** — implement only what is needed to make the
   failing test pass. No speculative code.
3. **Refactor under green** — clean up duplication or design issues only after
   all tests are passing. Never refactor while tests are red.

---

## Test file conventions

- Mirror the source tree: `src/foo/bar.py` → `tests/foo/test_bar.py`
- Name tests descriptively: `test_<function>_<scenario>_<expected_outcome>`
- One logical assertion per test; use multiple tests for multiple behaviours
- Mark integration tests with `@pytest.mark.integration` and unit tests with
  `@pytest.mark.unit`

---

## Coverage requirements

| Scope | Minimum coverage |
|---|---|
| New modules | 90 % line coverage |
| Modified functions | 100 % branch coverage on changed paths |
| Bug fixes | Regression test required — the fix must be proven by a test that was red before the fix |

Run coverage before raising a PR:

```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=90
```

---

## Tooling

- **Test runner**: `pytest`
- **Coverage**: `pytest-cov`
- **Mocking**: `unittest.mock` or `pytest-mock` — mock only external I/O and
  third-party services; never mock the code under test
- **Fixtures**: define shared fixtures in `conftest.py` at the nearest common
  ancestor, not inside individual test files

---

## Things you must not do

- Write production code before a failing test exists for that behaviour
- Commit with `# noqa` or `# type: ignore` to silence test or type errors
  instead of fixing them
- Skip tests with `@pytest.mark.skip` without a linked ticket and expiry date
- Use `assert` in production code as a substitute for proper error handling —
  assertions are for tests only
- Merge a PR where the CI test suite is red

---

## When generating or modifying code

Before writing any implementation, Claude must:

1. State which test file will cover the new behaviour
2. Show the failing test first
3. Only then write the production code

If a task description contains no testable acceptance criteria, ask the user to
define them before proceeding.
