from datetime import date

from sqlalchemy.orm import Session

from test_material_daily import setup


def test_customer_quality_stock_selection_binding_and_void(setup):
    from backend.app.models import Bottle, BottleSource, BottleSpec

    client, engine, _, actor = setup
    with Session(engine, expire_on_commit=False) as db:
        source_a = BottleSource(name="瓶号选择客户A", is_default=True)
        source_b = BottleSource(name="瓶号选择客户B")
        spec = BottleSpec(name="瓶号选择规格")
        db.add_all([source_a, source_b, spec])
        db.flush()
        good_bad = Bottle(
            body_code="SELECT-A-GOOD-BAD", source_id=source_a.id, spec_id=spec.id,
            zone="GOOD", process_status="INSPECTED", coding_date=date(2026, 10, 1), coded_by=actor.id,
        )
        good_scrap = Bottle(
            body_code="SELECT-A-GOOD-SCRAP", source_id=source_a.id, spec_id=spec.id,
            zone="GOOD", process_status="INSPECTED", coding_date=date(2026, 10, 2), coded_by=actor.id,
        )
        other_bad = Bottle(
            body_code="SELECT-B-BAD", source_id=source_b.id, spec_id=spec.id,
            zone="BAD", process_status="INSPECTED", coding_date=date(2026, 10, 1), coded_by=actor.id,
        )
        db.add_all([good_bad, good_scrap, other_bad])
        db.commit()
        source_a_id, source_b_id, spec_id = source_a.id, source_b.id, spec.id
        bad_id, scrap_id = good_bad.id, good_scrap.id

    marked_bad = client.put(f"/api/bottles/{bad_id}/status", json={"zone": "BAD", "note": "阀座损伤"})
    assert marked_bad.status_code == 200, marked_bad.text
    assert marked_bad.json()["returned_to_customer"] is True
    marked_scrap = client.put(f"/api/bottles/{scrap_id}/status", json={"zone": "SCRAP", "note": "瓶体报废"})
    assert marked_scrap.status_code == 200, marked_scrap.text

    stock_a = client.get("/api/quick-outbound/availability", params={"source_id": source_a_id}).json()[str(spec_id)]
    stock_b = client.get("/api/quick-outbound/availability", params={"source_id": source_b_id}).json()[str(spec_id)]
    assert (stock_a["bad"], stock_a["scrap"]) == (1, 1)
    assert (stock_a["selectable_bad"], stock_a["selectable_scrap"]) == (1, 1)
    assert (stock_b["bad"], stock_b["scrap"]) == (1, 0)

    candidates = client.get("/api/quick-outbound/bottle-candidates", params={
        "source_id": source_a_id, "spec_id": spec_id, "zone": "BAD",
        "date_from": "2026-10-01", "date_to": "2026-10-01", "body_code": "GOOD-BAD",
    })
    assert candidates.status_code == 200, candidates.text
    assert [item["id"] for item in candidates.json()["items"]] == [bad_id]

    outbound = client.post("/api/quick-outbound", json={
        "business_date": "2026-10-07", "source_id": source_a_id, "handler": "测试出库",
        "lines": [{
            "spec_id": spec_id, "bad_quantity": 1, "scrap_quantity": 1,
            "bad_bottle_ids": [bad_id], "scrap_bottle_ids": [scrap_id],
        }],
    })
    assert outbound.status_code == 201, outbound.text
    allocations = outbound.json()["lines"][0]["selected_bottles"]
    assert {(item["origin_zone"], item["body_code"]) for item in allocations} == {
        ("BAD", "SELECT-A-GOOD-BAD"), ("SCRAP", "SELECT-A-GOOD-SCRAP"),
    }
    assert {item["inspection_note"] for item in allocations} == {"阀座损伤", "瓶体报废"}
    receipt = client.post("/api/bottle-receipt/preview", json={"outbound_ids": [outbound.json()["id"]]})
    assert receipt.status_code == 200, receipt.text
    quality = receipt.json()["documents"][0]["quality_bottles"]
    assert {(item["zone"], item["body_code"], item["note"]) for item in quality} == {
        ("BAD", "SELECT-A-GOOD-BAD", "阀座损伤"),
        ("SCRAP", "SELECT-A-GOOD-SCRAP", "瓶体报废"),
    }
    assert client.get("/api/bottles", params={"body_code": "SELECT-B-BAD"}).json()["items"][0]["zone"] == "BAD"

    voided = client.post(f"/api/bottle-outbounds/{outbound.json()['id']}/void")
    assert voided.status_code == 200, voided.text
    assert all(not item["is_active"] for item in voided.json()["lines"][0]["selected_bottles"])
    assert client.get("/api/bottles", params={"body_code": "SELECT-A-GOOD-BAD"}).json()["items"][0]["zone"] == "BAD"
    assert client.get("/api/bottles", params={"body_code": "SELECT-A-GOOD-SCRAP"}).json()["items"][0]["zone"] == "SCRAP"

    quantity_only = client.post("/api/quick-outbound", json={
        "business_date": "2026-10-07", "source_id": source_a_id, "handler": "仅扣数量",
        "lines": [{"spec_id": spec_id, "bad_quantity": 1}],
    })
    assert quantity_only.status_code == 201, quantity_only.text
    assert quantity_only.json()["lines"][0]["selected_bottles"] == []
    assert client.get("/api/bottles", params={"body_code": "SELECT-A-GOOD-BAD"}).json()["items"][0]["zone"] == "BAD"
    remaining = client.get("/api/quick-outbound/availability", params={"source_id": source_a_id}).json()[str(spec_id)]
    assert remaining["bad"] == 0
    assert remaining["selectable_bad"] == 0
    stale_candidate = client.get("/api/quick-outbound/bottle-candidates", params={
        "source_id": source_a_id, "spec_id": spec_id, "zone": "BAD",
    })
    assert stale_candidate.status_code == 200, stale_candidate.text
    assert stale_candidate.json()["total"] == 0
    assert stale_candidate.json()["items"] == []
