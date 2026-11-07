# AI Code Review Assistant

A FastAPI service that reviews code or unified diffs with an LLM, then **checks the AI's own suggested tests before showing them**.
Built to demonstrate: scalable API design, automated testing, CI, telemetry, and critical review of AI output.

## Features
- `POST /review` takes code or a git diff and returns severity-ranked issues plus suggested pytest tests.
- **AI output validation:** suggested tests are parsed with `ast` (never executed) and flagged if they have syntax errors,
  no assertions, no `test_*` functions, or risky imports/calls (`os`, `subprocess`, `eval`, `open`, ...).
- **Defensive parsing:** tolerates markdown fences, chatter around JSON, odd severity labels; bad output returns a clear `502`.
- **Prompt-injection hardening:** reviewed code is wrapped in `<code>` tags and declared untrusted in the system prompt.
- **Telemetry:** structured JSON request logs, `X-Request-ID` header, and `GET /metrics` (counts, error rate, p50/p95 latency,
  issues by severity, % of AI tests that passed validation).
- **Dashboard** at `/` to try reviews and watch live metrics.
- **Provider-agnostic:** `mock` (offline, default), `anthropic`, or `openai`.

## Run it
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # open http://localhost:8000
```
Use a real model:
```bash
export LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-...   # or LLM_PROVIDER=openai OPENAI_API_KEY=...
```
Optionally set `LLM_MODEL` to override the default model.

Try the API:
```bash
curl -s localhost:8000/review -H 'content-type: application/json' \
  -d '{"code":"x = eval(input())","language":"python"}' | python -m json.tool
```

## Test
```bash
pytest --cov=app --cov-report=term-missing
```
CI (`.github/workflows/ci.yml`) runs the suite on Python 3.11 and 3.12 with an 85% coverage gate on every push and PR.
Tests use a fake LLM, so they are fast, deterministic and need no API key.

## Project layout
```
app/
  main.py        FastAPI app factory, middleware, endpoints
  reviewer.py    prompt building + defensive JSON parsing
  llm.py         Mock / Anthropic / OpenAI clients
  validator.py   static checks on AI-generated tests
  diff_utils.py  unified diff detection + added-line extraction
  metrics.py     thread-safe counters and latency percentiles
  schemas.py     Pydantic models
  static/        dashboard
tests/           pytest suite
```

## Ideas to extend
- GitHub webhook that reviews PRs and posts inline comments.
- Run suggested tests in a sandbox container and track the pass rate as a metric.
- Prometheus `/metrics` format and a Grafana dashboard.
- Rate limiting and API-key auth.
