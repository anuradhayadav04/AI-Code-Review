import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app import reviewer
from app.llm import LLMError, get_llm
from app.metrics import Metrics
from app.schemas import ReviewRequest, ReviewResponse
from app.validator import validate_python_tests

log = logging.getLogger("review")
logging.basicConfig(level=logging.INFO, format="%(message)s")
STATIC = Path(__file__).parent / "static"


def create_app(llm=None, metrics: Metrics | None = None) -> FastAPI:
    app = FastAPI(title="AI Code Review Assistant", version="1.0.0")
    app.state.metrics = metrics or Metrics()
    app.state.llm = llm  # resolved lazily so config errors surface as 502, not at import

    @app.middleware("http")
    async def observe(request: Request, call_next):
        start = time.perf_counter()
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            ms = (time.perf_counter() - start) * 1000
            if request.url.path.startswith("/review"):
                app.state.metrics.record_request(ms, status)
            log.info(json.dumps({"event": "request", "id": request_id, "method": request.method,
                                 "path": request.url.path, "status": status, "ms": round(ms, 1)}))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics_endpoint():
        return app.state.metrics.snapshot()

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(STATIC / "index.html")

    @app.post("/review", response_model=ReviewResponse)
    async def review(req: ReviewRequest, request: Request):
        m: Metrics = app.state.metrics
        started = time.perf_counter()
        try:
            client = app.state.llm or get_llm()
            kind, prompt = reviewer.build_user_prompt(req.code, req.language, req.filename)
            raw = await client.complete(reviewer.SYSTEM_PROMPT, prompt)
            result = reviewer.parse_llm_json(raw)
        except (LLMError, reviewer.ReviewParseError) as exc:
            m.record_llm_failure()
            raise HTTPException(status_code=502, detail=str(exc))

        check = None
        if req.language.lower() == "python" and result.suggested_tests:
            check = validate_python_tests(result.suggested_tests)
            m.record_test_check(check.valid)
        m.record_issues(i.severity for i in result.issues)

        return ReviewResponse(
            request_id=request.state.request_id,
            summary=result.summary,
            issues=result.issues,
            suggested_tests=result.suggested_tests,
            test_check=check,
            input_kind=kind,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    return app


app = create_app()
