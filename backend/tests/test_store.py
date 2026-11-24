import datetime
import pytest
from backend.store import AppointmentStore, parse_spoken_date, tz


@pytest.fixture
def clean_store():
    store = AppointmentStore()
    return store


def test_seed_data_counts(clean_store):
    doctors = clean_store.doctors
    assert len(doctors) >= 6
    specialities = {d["speciality"] for d in doctors.values()}
    assert len(specialities) >= 4
    # Check slots count (7 doctors * 5 days * 12 slots = 420)
    assert len(clean_store.slots) >= 300


def test_parse_spoken_date():
    today = datetime.datetime.now(tz).date()
    assert parse_spoken_date("today") == today.isoformat()
    assert parse_spoken_date("tomorrow") == (today + datetime.timedelta(days=1)).isoformat()
    # Check specific weekday
    parsed = parse_spoken_date("monday")
    assert parsed is not None
    # Check ISO format
    assert parse_spoken_date("2026-12-01") == "2026-12-01"


def test_check_availability_by_doctor_and_speciality(clean_store):
    res = clean_store.check_availability(doctor_name="Sharma")
    assert res["ok"] is True
    assert len(res["matches"]) >= 1
    assert "Sharma" in res["matches"][0]["doctor_name"]
    assert len(res["matches"][0]["slots"]) <= 6

    res_spec = clean_store.check_availability(speciality="Cardiology")
    assert res_spec["ok"] is True
    assert len(res_spec["matches"]) >= 1
    for m in res_spec["matches"]:
        assert m["speciality"] == "Cardiology"


def test_check_availability_fallback_alternatives(clean_store):
    # Non-existent doctor and non-existent speciality
    res = clean_store.check_availability(doctor_name="NonExistentSurgeonXYZ")
    assert res["ok"] is True
    assert res["is_alternative"] is True
    assert len(res["matches"]) > 0


def test_book_and_cancel_appointment(clean_store):
    # Check availability to get a valid slot
    avail = clean_store.check_availability(doctor_name="Sharma", date="today")
    assert len(avail["matches"]) > 0
    slot = avail["matches"][0]["slots"][0]
    doctor_id = avail["matches"][0]["doctor_id"]
    slot_id = slot["slot_id"]

    # 1. Book appointment
    book_res = clean_store.book_appointment(
        doctor_id=doctor_id,
        slot_id=slot_id,
        patient_name="Rahul Verma",
        phone_number="9876543210",
        phone_confirmed=True,
    )
    assert book_res["ok"] is True
    apt = book_res["appointment"]
    apt_id = apt["appointment_id"]
    assert apt["status"] == "active"
    assert clean_store.slots[slot_id]["is_booked"] is True

    # 2. Verify double-booking rejected
    double_res = clean_store.book_appointment(
        doctor_id=doctor_id,
        slot_id=slot_id,
        patient_name="Another Patient",
        phone_number="9123456789",
        phone_confirmed=True,
    )
    assert double_res["ok"] is False
    assert "already booked" in double_res["error"]

    # 3. Verify same patient duplicate booking with same doctor at same time rejected
    dup_res = clean_store.book_appointment(
        doctor_id=doctor_id,
        slot_id=slot_id,
        patient_name="Rahul Verma",
        phone_number="9876543210",
        phone_confirmed=True,
    )
    assert dup_res["ok"] is False

    # 4. Cancel appointment
    cancel_res = clean_store.cancel_appointment(
        phone_number="9876543210",
        phone_confirmed=True,
        appointment_id=apt_id,
    )
    assert cancel_res["ok"] is True
    assert cancel_res["appointment_id"] == apt_id
    assert clean_store.slots[slot_id]["is_booked"] is False
    assert clean_store.appointments[apt_id]["status"] == "cancelled"


def test_cancel_only_own_appointment(clean_store):
    avail = clean_store.check_availability(doctor_name="Sharma")
    slot = avail["matches"][0]["slots"][0]

    clean_store.book_appointment(
        doctor_id=avail["matches"][0]["doctor_id"],
        slot_id=slot["slot_id"],
        patient_name="Caller A",
        phone_number="9876543210",
        phone_confirmed=True,
    )

    # Caller B attempts to cancel
    cancel_res = clean_store.cancel_appointment(
        phone_number="9111122222",
        phone_confirmed=True,
    )
    assert cancel_res["ok"] is False
    assert "No active appointments found" in cancel_res["error"]


def test_multiple_appointments_disambiguation(clean_store):
    avail1 = clean_store.check_availability(doctor_name="Sharma")
    slot1 = avail1["matches"][0]["slots"][0]
    slot2 = avail1["matches"][0]["slots"][1]
    doc_id = avail1["matches"][0]["doctor_id"]

    clean_store.book_appointment(
        doctor_id=doc_id,
        slot_id=slot1["slot_id"],
        patient_name="Sunil Kumar",
        phone_number="9998887776",
        phone_confirmed=True,
    )
    clean_store.book_appointment(
        doctor_id=doc_id,
        slot_id=slot2["slot_id"],
        patient_name="Sunil Kumar",
        phone_number="9998887776",
        phone_confirmed=True,
    )

    # Cancel without appointment_id should trigger disambiguation
    cancel_res = clean_store.cancel_appointment(
        phone_number="9998887776",
        phone_confirmed=True,
    )
    assert cancel_res["ok"] is False
    assert cancel_res.get("needs_disambiguation") is True
    assert len(cancel_res["appointments"]) == 2
