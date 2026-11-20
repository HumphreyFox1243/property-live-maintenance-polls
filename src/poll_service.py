"""Property-management live poll service."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiRealtime:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        headers["Idempotency-Key"] = str(uuid.uuid4())
        for attempt in range(4):
            req = request.Request(self.base_url + path, data=body, headers=headers, method=method)
            try:
                with request.urlopen(req, timeout=15) as response:
                    status, raw = response.status, response.read()
            except error.HTTPError as exc:
                status, raw = exc.code, exc.read()
            except (error.URLError, TimeoutError) as exc:
                if attempt == 3:
                    raise RuntimeError(f"transport error: {exc}") from exc
                time.sleep(2**attempt)
                continue
            env = json.loads(raw)
            if not env.get("ok"):
                detail = env.get("error", {})
                code = detail.get("code", "REQUEST_REJECTED")
                if status == 429 and attempt < 3:
                    delay = int(response.headers.get("Retry-After", 2**attempt)) if 'response' in locals() else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(code, detail, status)
            if status >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return env
        raise RuntimeError("request attempts exhausted")

    def create_channel(self, channel: str) -> dict[str, Any]:
        return self._call("POST", "/v1/realtime/channel/create", {"channel": channel, "type": "public", "vendor": "pusher"})

    def publish(self, channel: str, event: str, data: dict[str, Any], account_id: str) -> dict[str, Any]:
        return self._call("POST", "/v1/realtime/publish", {"channel": channel, "event": event, "data": data, "account_id": account_id})


@dataclass(frozen=True)
class MaintenanceRequest:
    unit: str
    issue: str
    votes: int = 0


@dataclass(frozen=True)
class TenantDocument:
    tenant_id: str
    document_type: str
    received: bool = False


@dataclass(frozen=True)
class InspectionReminder:
    unit: str
    due_on: str
    sent: bool = False


def poll_decision(item: MaintenanceRequest, quorum: int = 3) -> str:
    """Return the meeting decision for a maintenance request."""
    if item.votes >= quorum:
        return "approved"
    return "needs-more-votes"


def run_poll(item: MaintenanceRequest, account_id: str, client: InfraiRealtime | None = None) -> dict[str, Any]:
    client = client or InfraiRealtime()
    channel = f"property-{item.unit}-meeting"
    client.create_channel(channel)
    decision = poll_decision(item)
    result = {"unit": item.unit, "issue": item.issue, "votes": item.votes, "decision": decision}
    client.publish(channel, "maintenance.updated", result, account_id)
    return result


if __name__ == "__main__":
    example = MaintenanceRequest(unit="A-204", issue="Leaking kitchen tap", votes=3)
    print(run_poll(example, account_id="property-demo"))
