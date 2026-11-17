from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from knowledge_enrichment.agents.schemas import Recommendation
from knowledge_enrichment.api import Services, create_app
from knowledge_enrichment.enrichment import AuditLog, JobManager


class FakeAdvisor:
    def __init__(self):
        self.calls = []

    def recommend(self, asset_type, asset_id, ticket_id, issue):
        self.calls.append((asset_type, asset_id, ticket_id, issue))
        return Recommendation(ticket_id=ticket_id, probable_cause="cause")


class FakeEngine:
    def __init__(self):
        self.processed = []

    def process(self, job_id, ticket):
        self.processed.append(ticket)


@pytest.fixture
def client(settings):
    settings.rate_limit_per_minute = 5
    engine = FakeEngine()
    services = Services(settings, FakeAdvisor(), JobManager(engine), AuditLog(settings.runtime_dir),
                        SimpleNamespace(installed={"a": 1}))
    c = TestClient(create_app(services))
    c.engine, c.advisor = engine, services.advisor
    return c


REC = {"assetId": "A1", "assetType": "battery", "ticketId": "INC-1", "issue": "hot", "loggedDate": "2026-11-17"}


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok", "installedSops": 1}


def test_recommendations_returns_camel_case(client):
    r = client.post("/api/recommendations", json=REC)
    assert r.status_code == 200
    body = r.json()
    assert body["probableCause"] == "cause" and "recommendedActions" in body and body["noRelevantKnowledge"] is False
    assert client.advisor.calls == [("battery", "A1", "INC-1", "hot")]


def test_asset_type_is_restricted_to_battery_or_station(client):
    assert client.post("/api/recommendations", json={**REC, "assetType": "dock"}).status_code == 422


def test_input_length_limits(client):
    assert client.post("/api/recommendations", json={**REC, "issue": "x" * 2001}).status_code == 422


def test_resolution_returns_202_and_only_checking_or_done(client):
    body = {"assetId": "A1", "assetType": "battery", "issue": "hot", "loggedDate": "2026-11-17",
            "criticality": "urgent", "fixApplied": "Replaced the connector and verified the handshake"}
    r = client.post("/api/tickets/INC-1/resolution", json=body)
    assert r.status_code == 202 and r.json()["status"] == "checking"
    job = r.json()["jobId"]
    import time
    for _ in range(50):
        status = client.get(f"/api/enrichment/{job}").json()
        if status["status"] == "done":
            break
        time.sleep(0.05)
    assert status == {"status": "done"}
    assert client.engine.processed[0].ticket_id == "INC-1"
    assert client.get("/api/enrichment/unknown").status_code == 404


def test_rate_limit(client):
    codes = [client.post("/api/recommendations", json=REC).status_code for _ in range(7)]
    assert codes[:5] == [200] * 5 and codes[5] == 429
