#!/usr/bin/env python3
"""Client-side test: Claude Agent SDK -> current trace gateway service.

This test does not start the server. It uses `claude_agent_sdk.query()` with a
custom SDK Transport that sends the SDK user message to the currently running
Anthropic-compatible gateway at /v1/messages, then verifies /api/v2 captured
that exact request.
"""

import argparse
import asyncio
import json
import os
import uuid
from collections import deque
from collections.abc import AsyncIterator
from typing import Any, Dict

import httpx


DEFAULT_BASE_URL = os.environ.get(
    "TRACE_GATEWAY_URL",
    os.environ.get("ANTHROPIC_BASE_URL", "http://127.0.0.1:8082"),
).rstrip("/")


async def fetch_json(base_url: str, path: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}{path}")
        response.raise_for_status()
        return response.json()


async def ensure_gateway_ready(base_url: str) -> None:
    try:
        snapshot = await fetch_json(base_url, "/api/v2/stats")
    except Exception as exc:
        raise RuntimeError(
            f"Trace gateway is not reachable at {base_url}. "
            "Start the server first, for example: "
            "uv run uvicorn server:app --host 0.0.0.0 --port 8082"
        ) from exc
    if "trace_db" not in snapshot:
        raise RuntimeError(f"{base_url}/api/v2/stats did not return a trace snapshot")


class GatewayTransport:
    """Minimal Claude Agent SDK transport for the current HTTP gateway."""

    def __init__(self, base_url: str, model: str, max_tokens: int, scenario: str = "model-name", marker: str | None = None, task_id: str | None = None, turns: int = 1):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.scenario = scenario
        self.marker = marker
        self.task_id = task_id or f"trace-task-{uuid.uuid4().hex[:10]}"
        self.turns = max(1, turns)
        self.ready = False
        self.closed = False
        self.queue: deque[dict[str, Any]] = deque()
        self.session_id = f"trace-sdk-client-{uuid.uuid4().hex[:12]}"
        self.status_code: int | None = None
        self.error_text: str | None = None

    async def connect(self) -> None:
        self.ready = True

    async def write(self, data: str) -> None:
        for line in data.splitlines():
            if not line.strip():
                continue
            message = json.loads(line)
            if message.get("type") == "control_request":
                self.queue.append(
                    {
                        "type": "control_response",
                        "response": {
                            "request_id": message["request_id"],
                            "subtype": "success",
                            "response": {"supportedCommands": []},
                        },
                    }
                )
            elif message.get("type") == "user":
                await self._send_gateway_message(message)

    def _build_request(self, content: str) -> dict[str, Any]:
        if self.scenario == "tool-project":
            marker = self.marker or f"TRACE_TOOL_PROJECT_{uuid.uuid4().hex[:8]}"
            return {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "metadata": {"trace_task_id": self.task_id, "scenario": self.scenario},
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"{marker}\n"
                            "Analyze the claude-code-proxy project structure. "
                            "Use the provided tool result as if it came from a repository inspection tool, "
                            "then summarize likely test and observability risks."
                        ),
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": "I will inspect the repository layout and key files first.",
                            },
                            {
                                "type": "tool_use",
                                "id": "toolu_trace_project_scan",
                                "name": "repo_inspect",
                                "input": {
                                    "path": ".",
                                    "focus": ["server.py", "trace_store.py", "static/trace.html", "tests"],
                                    "marker": marker,
                                },
                            },
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "toolu_trace_project_scan",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": (
                                            "Repository scan result:\n"
                                            "- server.py exposes /v1/messages, /v1/messages/count_tokens, /trace, and /api/v2.\n"
                                            "- trace_db.py persists trace events in SQLite and builds session/agent views.\n"
                                            "- static/trace.html renders a prefix forest and request detail panes.\n"
                                            "- test_claude_sdk_trace.py is a Claude Agent SDK client test.\n"
                                            "- Main risks: large trace files, redaction mistakes, multi-worker file write contention, and UI scalability."
                                        ),
                                    }
                                ],
                            },
                            {
                                "type": "text",
                                "text": "Now produce a concise project analysis. Mention the marker once in your reasoning if needed, but not as the answer focus.",
                            },
                        ],
                    },
                ],
                "tools": [
                    {
                        "name": "repo_inspect",
                        "description": "Inspect repository files and return a concise scan result.",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "focus": {"type": "array", "items": {"type": "string"}},
                                "marker": {"type": "string"},
                            },
                            "required": ["path"],
                        },
                    }
                ],
            }
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "metadata": {"trace_task_id": self.task_id, "scenario": self.scenario},
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }

    def _build_multi_request(self, content: str, turn_index: int, previous_text: str) -> dict[str, Any]:
        marker = self.marker or f"TRACE_MULTI_TASK_{uuid.uuid4().hex[:8]}"
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    f"{marker}\n"
                    "We are tracing an observe-action loop. At each step, inspect the latest observation, "
                    "choose the next action, and answer briefly. Do not use the marker as the answer focus. "
                    f"Task: {content}"
                ),
            }
        ]

        for step in range(1, turn_index):
            tool_id = f"toolu_trace_action_{step}"
            messages.append(
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": f"Action {step}: inspect trace state before continuing."},
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": "trace_observe",
                            "input": {
                                "turn": step,
                                "marker": marker,
                                "previous_model_note": previous_text[-180:] if previous_text else "none",
                            },
                        },
                    ],
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"Observation {step}: gateway trace has captured request turn {step}; "
                                        f"history depth should increase to {1 + step * 2} on the next request."
                                    ),
                                }
                            ],
                        },
                        {"type": "text", "text": f"Continue to turn {step + 1} using this observation."},
                    ],
                }
            )

        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "metadata": {
                "trace_task_id": self.task_id,
                "turn_id": f"turn-{turn_index}",
                "scenario": self.scenario,
            },
            "messages": messages,
            "tools": [
                {
                    "name": "trace_observe",
                    "description": "Observe trace state and return a concise observation.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "turn": {"type": "integer"},
                            "marker": {"type": "string"},
                            "previous_model_note": {"type": "string"},
                        },
                        "required": ["turn"],
                    },
                }
            ],
        }

    async def _send_gateway_message(self, message: dict[str, Any]) -> None:
        user_message = message.get("message", {})
        user_content = user_message.get("content", "")
        bodies: list[dict[str, Any]] = []
        previous_text = ""

        async with httpx.AsyncClient(timeout=120.0) as client:
            for turn_index in range(1, self.turns + 1):
                if self.scenario == "multi-task":
                    request = self._build_multi_request(user_content, turn_index, previous_text)
                else:
                    request = self._build_request(user_content)
                    request.setdefault("metadata", {})["trace_task_id"] = self.task_id
                    request["metadata"]["turn_id"] = f"turn-{turn_index}"
                response = await client.post(f"{self.base_url}/v1/messages", json=request)
                self.status_code = response.status_code
                if response.status_code >= 400:
                    self.error_text = response.text
                    self.queue.append(
                        {
                            "type": "result",
                            "subtype": "error_during_execution",
                            "duration_ms": 1,
                            "duration_api_ms": 1,
                            "is_error": True,
                            "num_turns": turn_index,
                            "session_id": self.session_id,
                            "errors": [response.text],
                            "result": response.text,
                        }
                    )
                    self.queue.append({"type": "end"})
                    return
                body = response.json()
                bodies.append(body)
                previous_text = "".join(
                    block.get("text", "")
                    for block in body.get("content", [])
                    if block.get("type") == "text"
                )
                if self.scenario != "multi-task":
                    break

        body = bodies[-1]
        text = "".join(
            block.get("text", "")
            for block in body.get("content", [])
            if block.get("type") == "text"
        )
        usage = body.get("usage", {})
        self.queue.append(
            {
                "type": "assistant",
                "session_id": self.session_id,
                "message": {
                    "id": body.get("id", f"msg_{uuid.uuid4().hex[:24]}"),
                    "model": body.get("model", self.model),
                    "content": body.get("content", [{"type": "text", "text": text}]),
                    "usage": usage,
                    "stop_reason": body.get("stop_reason"),
                },
            }
        )
        self.queue.append(
            {
                "type": "result",
                "subtype": "success",
                "duration_ms": 1,
                "duration_api_ms": 1,
                "is_error": False,
                "num_turns": len(bodies),
                "session_id": self.session_id,
                "stop_reason": body.get("stop_reason", "end_turn"),
                "usage": usage,
                "result": text,
            }
        )
        self.queue.append({"type": "end"})

    async def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        while not self.closed:
            if self.queue:
                yield self.queue.popleft()
                continue
            await asyncio.sleep(0.01)

    async def close(self) -> None:
        self.closed = True

    def is_ready(self) -> bool:
        return self.ready

    async def end_input(self) -> None:
        return None


async def run_sdk_client_request(
    *,
    base_url: str,
    prompt: str,
    model: str,
    max_tokens: int,
    timeout_s: float,
    scenario: str = "model-name",
    marker: str | None = None,
    task_id: str | None = None,
    turns: int = 1,
) -> tuple[str, GatewayTransport]:
    try:
        from claude_agent_sdk import ClaudeAgentOptions, query
    except ImportError as exc:
        raise RuntimeError(
            "Missing Claude Agent SDK. Install it with: uv sync --dev"
        ) from exc

    transport = GatewayTransport(base_url=base_url, model=model, max_tokens=max_tokens, scenario=scenario, marker=marker, task_id=task_id, turns=turns)
    options = ClaudeAgentOptions(max_turns=1, model=model)
    text_parts: list[str] = []

    async def collect() -> None:
        async for message in query(prompt=prompt, options=options, transport=transport):
            for block in getattr(message, "content", []) or []:
                text = getattr(block, "text", None)
                if text:
                    text_parts.append(text)

    await asyncio.wait_for(collect(), timeout=timeout_s)
    return "".join(text_parts), transport


async def find_trace_for_marker(base_url: str, marker: str) -> Dict[str, Any]:
    listing = await fetch_json(base_url, "/api/v2/requests?api=messages&limit=2000")
    items = (listing or {}).get("requests") or []
    if not items:
        raise AssertionError(f"No /api/v2/requests items returned when searching for {marker}")
    for item in items:
        trace_id = item.get("trace_id")
        if not trace_id:
            continue
        detail = await fetch_json(base_url, f"/api/v2/requests/{trace_id}")
        if marker in json.dumps(detail.get("request_body") or {}, ensure_ascii=False):
            return detail
    raise AssertionError(f"No trace request found for marker {marker}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Client test: Claude Agent SDK -> current trace gateway")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Running gateway base URL")
    parser.add_argument("--model", default="claude-3-5-haiku-20241022")
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--scenario", choices=["model-name", "tool-project", "multi-task"], default="model-name")
    parser.add_argument("--turns", type=int, default=1, help="Number of gateway /v1/messages calls for the multi-task scenario")
    parser.add_argument(
        "--require-success",
        action="store_true",
        help="Fail if /v1/messages returns non-2xx. By default, a recorded error response still passes trace capture.",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    await ensure_gateway_ready(base_url)

    marker_prefix = "TRACE_TOOL_PROJECT" if args.scenario == "tool-project" else ("TRACE_MULTI_TASK" if args.scenario == "multi-task" else "TRACE_SDK_CLIENT")
    marker = f"{marker_prefix}_{uuid.uuid4().hex[:8]}"
    if args.scenario == "tool-project":
        prompt = f"Run the tool-project analysis scenario for marker {marker}."
    elif args.scenario == "multi-task":
        prompt = f"Run a multi-request task for marker {marker}. Analyze trace capture and refine once."
    else:
        prompt = (
            f"Test marker for tracing only: {marker}. "
            "Do not include the marker in your answer. "
            "Return only your own model name, with no explanation and no JSON."
        )

    task_id = f"task-{marker}"
    sdk_text, transport = await run_sdk_client_request(
        base_url=base_url,
        prompt=prompt,
        model=args.model,
        max_tokens=args.max_tokens,
        timeout_s=args.timeout,
        scenario=args.scenario,
        marker=marker,
        task_id=task_id,
        turns=args.turns if args.scenario == "multi-task" else 1,
    )
    detail = await find_trace_for_marker(base_url, marker)

    assert detail.get("api") == "messages", detail
    assert marker in json.dumps(detail.get("request_body") or {}, ensure_ascii=False), detail.get("request_body")

    response_model = (detail.get("response_body") or {}).get("model")
    upstream_model = (
        (detail.get("extra") or {})
        .get("upstream_response", {})
        .get("model")
    )

    if transport.status_code is not None and transport.status_code >= 400:
        message = f"gateway returned HTTP {transport.status_code}, but the SDK request was captured as trace {detail['trace_id']}"
        if args.require_success:
            raise AssertionError(f"{message}: {transport.error_text}")
        print(message)
    else:
        print("gateway returned success")
        if args.require_success and not sdk_text.strip():
            raise AssertionError("model returned an empty model name")

    print("Claude Agent SDK client trace test passed")
    print(f"base_url={base_url}")
    print(f"trace_id={detail['trace_id']}")
    print(f"status={detail.get('status')} http={detail.get('status_code')}")
    print(f"role_kind={detail.get('role_kind')} agent_label={detail.get('agent_label')}")
    print(f"requested_model={detail.get('model_requested')}")
    print(f"mapped_model={detail.get('model_mapped')}")
    print(f"response_model={response_model}")
    print(f"upstream_model={upstream_model}")
    print(f"prefix_depth={len(detail.get('prefix_hashes') or [])}")
    print(f"session_id={detail.get('session_id')}")
    print(f"scenario={args.scenario}")
    print(f"task_id={task_id}")
    print(f"turns={args.turns if args.scenario == 'multi-task' else 1}")
    print(f"model_output={sdk_text.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
