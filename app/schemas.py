from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.config import MAX_CODE_CHARS

Severity = Literal["info", "low", "medium", "high"]


class ReviewRequest(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS,
                      description="Source code or a unified diff.")
    language: str = Field(default="python", max_length=20)
    filename: Optional[str] = Field(default=None, max_length=200)


class Issue(BaseModel):
    severity: Severity = "info"
    line: Optional[int] = None
    message: str
    suggestion: Optional[str] = None

    @field_validator("severity", mode="before")
    @classmethod
    def _normalise_severity(cls, v):
        v = str(v).strip().lower()
        aliases = {"critical": "high", "major": "high", "minor": "low",
                   "warning": "medium", "error": "high"}
        v = aliases.get(v, v)
        return v if v in ("info", "low", "medium", "high") else "info"

    @field_validator("line", mode="before")
    @classmethod
    def _coerce_line(cls, v):
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None


class LLMReview(BaseModel):
    """The structure we ask the model to return."""
    summary: str
    issues: list[Issue] = []
    suggested_tests: str = ""


class TestCheck(BaseModel):
    __test__ = False  # stop pytest trying to collect this class
    valid: bool
    test_count: int
    assertion_count: int
    problems: list[str]


class ReviewResponse(BaseModel):
    request_id: str
    summary: str
    issues: list[Issue]
    suggested_tests: str
    test_check: Optional[TestCheck] = None
    input_kind: Literal["code", "diff"]
    latency_ms: float
