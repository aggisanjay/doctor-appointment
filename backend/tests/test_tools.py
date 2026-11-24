import pytest
from backend.store import store
from backend.tools import (
    book_appointment_logic,
    cancel_appointment_logic,
    check_doctor_availability_logic,
)


@pytest.fixture(autouse=True)
def reset_store():
    store.seed_data()


def test_tool_unconfirmed_phone_rejected():
    res = book_appointment_logic(
        doctor_id="doc_sharma",
        slot_id="any_slot",
        patient_name="Amit Shah",
        phone_number="9876543210",
        phone_confirmed=False,  # Unconfirmed!
    )
    assert res["ok"] is False
    assert "not explicitly confirmed" in res["error"]

    cancel_res = cancel_appointment_logic(
        phone_number="9876543210",
        phone_confirmed=False,  # Unconfirmed!
    )
    assert cancel_res["ok"] is False
    assert "not explicitly confirmed" in cancel_res["error"]


def test_tool_spoken_digits_normalized():
    avail = check_doctor_availability_logic(doctor_name="Sharma")
    assert avail["ok"] is True
    slot = avail["matches"][0]["slots"][0]
    doc_id = avail["matches"][0]["doctor_id"]

    # Book with spoken phone number
    res = book_appointment_logic(
        doctor_id=doc_id,
        slot_id=slot["slot_id"],
        patient_name="Deepak Joshi",
        phone_number="plus nine one nine eight seven six five four three two one zero",
        phone_confirmed=True,
    )
    assert res["ok"] is True
    assert res["appointment"]["phone_number"] == "9876543210"

    # Cancel with word digits
    cancel_res = cancel_appointment_logic(
        phone_number="nine eight seven six five four three two one zero",
        phone_confirmed=True,
        appointment_id=res["appointment"]["appointment_id"],
    )
    assert cancel_res["ok"] is True


def test_tool_invalid_phone_rejected():
    avail = check_doctor_availability_logic(doctor_name="Sharma")
    slot = avail["matches"][0]["slots"][0]
    doc_id = avail["matches"][0]["doctor_id"]

    res = book_appointment_logic(
        doctor_id=doc_id,
        slot_id=slot["slot_id"],
        patient_name="Test Patient",
        phone_number="12345",  # Invalid!
        phone_confirmed=True,
    )
    assert res["ok"] is False
    assert "must be exactly 10 digits" in res["error"]
