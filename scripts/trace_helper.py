"""
Hermes Agent 트레이스 헬퍼
- OpenTelemetry 호환 트레이스 ID/스팬 ID 생성
- 컨텍스트 변수로 비동기/백그라운드 프로세스 간 전파
- Phoenix/Langfuse 등 오픈소스 옵저버빌리티 도구 연동용 JSONL 출력
"""
import uuid
import time
import os
import json
from contextvars import ContextVar
from functools import wraps
from typing import Any, Optional
from datetime import datetime

# ─── 컨텍스트 변수 (비동기/스레드/프로세스 안전) ───
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_stack: ContextVar[list] = ContextVar("span_stack", default=[])

# ─── 설정 ───
TRACE_LOG_FILE = os.environ.get("HERMES_TRACE_LOG", "")
ENABLE_CONSOLE = os.environ.get("HERMES_TRACE_CONSOLE", "1") == "1"


def new_trace(name: str = "hermes") -> str:
    """새 트레이스 시작 (루트 스팬 생성)"""
    tid = f"{name}-{uuid.uuid4().hex[:8]}"
    _trace_id.set(tid)
    _span_stack.set([])
    _log_trace_event("trace_start", {"trace_id": tid, "name": name})
    return tid


def get_trace_id() -> str:
    """현재 트레이스 ID 반환 (없으면 새로 생성)"""
    tid = _trace_id.get()
    if not tid:
        tid = new_trace()
    return tid


def set_trace_id(tid: str) -> None:
    """외부에서 트레이스 ID 주입 (백그라운드 프로세스 전파용)"""
    _trace_id.set(tid)
    _span_stack.set([])


def start_span(name: str, reason: str = "", **attrs) -> dict:
    """스팬 시작 - 결정 이유(reason) 필수"""
    span = {
        "span_id": uuid.uuid4().hex[:8],
        "name": name,
        "reason": reason,
        "attrs": attrs,
        "start": time.time(),
        "start_iso": datetime.now().isoformat(),
        "parent": _span_stack.get()[-1]["span_id"] if _span_stack.get() else None,
    }
    stack = _span_stack.get()
    stack.append(span)
    _span_stack.set(stack)
    return span


def end_span(span: dict, result: str = "ok", **extra) -> None:
    """스팬 종료"""
    span["end"] = time.time()
    span["end_iso"] = datetime.now().isoformat()
    span["duration_ms"] = int((span["end"] - span["start"]) * 1000)
    span["result"] = result
    span["attrs"].update(extra)
    
    # 스택에서 제거
    stack = _span_stack.get()
    if stack and stack[-1]["span_id"] == span["span_id"]:
        stack.pop()
        _span_stack.set(stack)
    
    _log_span(span)


def _log_span(span: dict) -> None:
    """스팬 로그 출력 (콘솔 + 파일)"""
    trace_id = get_trace_id()
    msg = (
        f"[TRACE] {trace_id} | {span['name']} | "
        f"{span['duration_ms']}ms | {span['reason']} | {span['result']}"
    )
    if ENABLE_CONSOLE:
        print(msg)
    if TRACE_LOG_FILE:
        log_entry = {
            "trace_id": trace_id,
            "span_id": span["span_id"],
            "parent_span_id": span["parent"],
            "name": span["name"],
            "reason": span["reason"],
            "start": span["start_iso"],
            "end": span["end_iso"],
            "duration_ms": span["duration_ms"],
            "result": span["result"],
            "attrs": span["attrs"],
        }
        try:
            with open(TRACE_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # 로그 실패해도 본체 영향 없음


def _log_trace_event(event: str, data: dict) -> None:
    """트레이스 레벨 이벤트 로그"""
    if TRACE_LOG_FILE:
        log_entry = {
            "trace_id": get_trace_id(),
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        try:
            with open(TRACE_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


# ─── 편의 데코레이터 ───
def traced(name: str, reason: str = ""):
    """함수에 트레이스 스팬 자동 추가"""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            span = start_span(name, reason)
            try:
                result = fn(*args, **kwargs)
                end_span(span, "ok", output_type=type(result).__name__)
                return result
            except Exception as e:
                end_span(span, "error", error=str(e), error_type=type(e).__name__)
                raise
        return wrapper
    return deco


# ─── 비동기 지원 ───
async def start_span_async(name: str, reason: str = "", **attrs) -> dict:
    return start_span(name, reason, **attrs)


async def end_span_async(span: dict, result: str = "ok", **extra) -> None:
    end_span(span, result, **extra)


# ─── 컨텍스트 매니저 (with 문 지원) ───
class Span:
    def __init__(self, name: str, reason: str = "", **attrs):
        self.name = name
        self.reason = reason
        self.attrs = attrs
        self.span = None
    
    def __enter__(self):
        self.span = start_span(self.name, self.reason, **self.attrs)
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            end_span(self.span, "error", error=str(exc_val), error_type=exc_type.__name__)
        else:
            end_span(self.span, "ok")
        return False  # 예외 전파


def span(name: str, reason: str = "", **attrs) -> Span:
    return Span(name, reason, **attrs)


# start_span도 컨텍스트 매니저로 쓰게 하려면 별도 함수 필요
# 기존 start_span은 dict 반환, span()은 Span 객체 반환


# ─── 백그라운드 프로세스용 헬퍼 ───
def inject_trace_env() -> dict:
    """자식 프로세스에 전달할 환경변수 반환"""
    return {"HERMES_TRACE_ID": get_trace_id()}


def extract_trace_env(env: dict = None) -> str:
    """환경변수에서 트레이스 ID 추출"""
    env = env or os.environ
    return env.get("HERMES_TRACE_ID", "")


# ─── Phoenix/Otel 호환 JSONL 내보내기 ───
def export_jsonl(output_path: str) -> int:
    """로그 파일을 Phoenix 호환 JSONL로 변환"""
    if not TRACE_LOG_FILE or not os.path.exists(TRACE_LOG_FILE):
        return 0
    count = 0
    with open(TRACE_LOG_FILE, "r", encoding="utf-8") as f_in, \
         open(output_path, "w", encoding="utf-8") as f_out:
        for line in f_in:
            try:
                entry = json.loads(line.strip())
                # OpenTelemetry 세맨틱 컨벤션 매핑
                if "span_id" in entry:
                    otel_entry = {
                        "traceId": entry["trace_id"].split("-")[-1].zfill(32),  # 32 hex chars
                        "spanId": entry["span_id"].zfill(16),
                        "parentSpanId": entry.get("parent_span_id", "").zfill(16) or None,
                        "name": entry["name"],
                        "startTimeUnixNano": int(entry["start"].replace("T", " ").replace("-", "").replace(":", "")[:14]) * 1_000_000_000,
                        "endTimeUnixNano": int(entry["end"].replace("T", " ").replace("-", "").replace(":", "")[:14]) * 1_000_000_000,
                        "attributes": {
                            "hermes.reason": entry["reason"],
                            "hermes.result": entry["result"],
                            **entry.get("attrs", {}),
                        },
                        "status": {"code": "OK" if entry["result"] == "ok" else "ERROR"},
                    }
                    f_out.write(json.dumps(otel_entry) + "\n")
                    count += 1
            except Exception:
                continue
    return count