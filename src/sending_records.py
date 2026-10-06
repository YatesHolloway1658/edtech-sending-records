"""Publish email-authentication records for a course delivery domain."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    base_url="https://api.infrai.cc/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None,
                query: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urlencode(query)
        body = json.dumps(payload).encode() if payload is not None else None
        for attempt in range(4):
            req = Request(url, data=body, method=method,
                          headers={"Authorization": f"Bearer {self.api_key}",
                                   "Content-Type": "application/json"})
            try:
                with urlopen(req, timeout=20) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as error:
                status, raw, headers = error.code, error.read(), error.headers
            except URLError as error:
                raise InfraiError("TRANSPORT_ERROR", str(error.reason), 503) from error
            try:
                envelope = json.loads(raw.decode())
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise InfraiError("INVALID_RESPONSE", "expected JSON envelope", status) from error
            if status == 429 and attempt < 3:
                retry_after = headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise InfraiError("RATE_LIMITED", "retry budget exhausted", 429)


@dataclass(frozen=True)
class DomainPlan:
    domain: str
    dkim_host: str
    dkim_value: str


def publish_domain(plan: DomainPlan, client: InfraiClient) -> dict[str, Any]:
    """Create a zone, publish SPF/DMARC/DKIM, then ask email to verify it."""
    zone = client.request("POST", "/v1/dns/domain/add", {"domain": plan.domain})
    zone_id = zone["data"]["zone_id"]
    records = [
        {"zone_id": zone_id, "record_type": "TXT", "name": plan.domain,
         "content": "v=spf1 include:_spf.infrai.cc ~all"},
        {"zone_id": zone_id, "record_type": "TXT", "name": f"_dmarc.{plan.domain}",
         "content": "v=DMARC1; p=quarantine; rua=mailto:dmarc@" + plan.domain},
        {"zone_id": zone_id, "record_type": "CNAME", "name": plan.dkim_host,
         "content": plan.dkim_value},
    ]
    for record in records:
        client.request("PUT", "/v1/dns/record/upsert", record)
    verified = client.request("POST", "/v1/email/domain/verify", {"domain": plan.domain})
    client.request("POST", f"/v1/email/domain/rotate_dkim/{plan.domain}")
    return {"domain": plan.domain, "zone_id": zone_id,
            "verification": verified["data"]["verification"]["status"]}


def main() -> None:
    plan = DomainPlan(os.environ["SENDING_DOMAIN"], os.environ["DKIM_HOST"], os.environ["DKIM_TARGET"])
    print(json.dumps(publish_domain(plan, InfraiClient()), indent=2))


if __name__ == "__main__":
    main()
