import json
import logging
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.store import store
from backend.tools import (
    book_appointment_logic,
    cancel_appointment_logic,
    check_doctor_availability_logic,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")


def print_separator(title: str):
    print("\n" + "=" * 65)
    print(f" {title}")
    print("=" * 65)


def print_dashboard_summary():
    doctors = store.get_doctors_overview()
    appointments = store.get_all_appointments()
    total_free = sum(d["total_free_slots"] for d in doctors)
    print(f"\n[DASHBOARD STATE]")
    print(f"Doctors: {len(doctors)} | Total Available Slots: {total_free} | Total Appointments: {len(appointments)}")
    if appointments:
        print("Recent Appointments:")
        for a in appointments[:3]:
            print(f"  - [{a['status'].upper()}] {a['appointment_id']}: {a['patient_name']} with {a['doctor_name']} on {a['date']} at {a['time']}")
    else:
        print("  (No appointments booked yet)")


def run_simulation():
    print_separator("STEP 2: TEXT-MODE CONVERSATION SIMULATION")
    print("Driving the exact Pipecat tool handlers through a simulated dialogue.\n")

    # Initial state
    print_dashboard_summary()

    # Turn 1: Availability Check
    print_separator("TURN 1: CALLER ASKS FOR AVAILABILITY")
    print("Caller: 'Hi, I need to see a cardiologist tomorrow morning.'")
    print("Agent: 'Let me check who is available for you tomorrow.' (Calling check_doctor_availability...)")

    avail_res = check_doctor_availability_logic(speciality="Cardiology", date="tomorrow")
    matches = avail_res.get("matches", [])
    print(f"\nTool Returned: {len(matches)} doctors matching Cardiology")
    for m in matches:
        print(f"  * {m['doctor_name']} ({m['speciality']}, {m['room']}):")
        slots_str = ", ".join(s["time"] for s in m["slots"][:3])
        print(f"    Available times: {slots_str}")

    target_doctor = matches[0]
    target_slot = target_doctor["slots"][0]
    print(f"\nAgent: '{target_doctor['doctor_name']} has an opening tomorrow at {target_slot['time']}. Would that work?'")

    # Turn 2: Unconfirmed Phone Guard Check
    print_separator("TURN 2: CALLER ACCEPTS; AGENT TESTS CONFIRMATION ENFORCEMENT")
    print("Caller: 'Yes, that works! My name is Rajesh Patel, number is 9876543210.'")
    print("\n[Simulating safety check: Attempting booking with phone_confirmed=False]")
    rejected_booking = book_appointment_logic(
        doctor_id=target_doctor["doctor_id"],
        slot_id=target_slot["slot_id"],
        patient_name="Rajesh Patel",
        phone_number="9876543210",
        phone_confirmed=False,
    )
    print(f"Tool Enforcement Result: ok={rejected_booking['ok']}, error='{rejected_booking.get('error')}'")
    assert rejected_booking["ok"] is False, "Safety guard must reject unconfirmed phone"

    # Turn 3: Agent Reads Back Number and Books
    print_separator("TURN 3: AGENT READS NUMBER BACK DIGIT-BY-DIGIT")
    print("Agent: 'I have your number as 9 8 7 6 5, 4 3 2 1 0. Is that correct?'")
    print("Caller: 'Yes, that is correct.'")
    print("\n[Calling book_appointment with spoken number words and phone_confirmed=True]")

    spoken_phone = "plus nine one nine eight seven six five four three two one zero"
    booked_res = book_appointment_logic(
        doctor_id=target_doctor["doctor_id"],
        slot_id=target_slot["slot_id"],
        patient_name="Rajesh Patel",
        phone_number=spoken_phone,
        phone_confirmed=True,
    )
    assert booked_res["ok"] is True, f"Booking failed: {booked_res}"
    apt = booked_res["appointment"]
    print(f"Tool Result: ok=True")
    print(f"Appointment ID: {apt['appointment_id']}")
    print(f"Confirmed Phone: {apt['phone_number']}")
    print(f"Doctor: {apt['doctor_name']} | Date: {apt['date']} at {apt['time']}")
    print(f"Agent: 'Your appointment with {apt['doctor_name']} on {apt['date']} at {apt['time']} is confirmed.'")

    print_dashboard_summary()

    # Turn 4: Double-booking Prevention
    print_separator("TURN 4: VERIFYING DOUBLE-BOOKING PREVENTED IN CODE")
    print("Another caller attempts to book the same slot at the same time:")
    double_res = book_appointment_logic(
        doctor_id=target_doctor["doctor_id"],
        slot_id=target_slot["slot_id"],
        patient_name="Sneha Rao",
        phone_number="9112233445",
        phone_confirmed=True,
    )
    print(f"Result: ok={double_res['ok']}, error='{double_res.get('error')}'")
    assert double_res["ok"] is False

    # Turn 5: Cancellation
    print_separator("TURN 5: CALLER CANCELS THE APPOINTMENT")
    print("Caller: 'I need to cancel my appointment.'")
    print("Agent: 'I can help with that. Confirming your number ending in 3210. Is that correct?'")
    print("Caller: 'Yes.'")

    cancel_res = cancel_appointment_logic(
        phone_number="9876543210",
        phone_confirmed=True,
        appointment_id=apt["appointment_id"],
    )
    print(f"Tool Result: ok={cancel_res['ok']}")
    print(f"Message: {cancel_res.get('message')}")
    assert cancel_res["ok"] is True
    print(f"Agent: '{cancel_res.get('message')}'")

    print_dashboard_summary()

    # Verify slot is restored
    slot_now = store.slots[target_slot["slot_id"]]
    assert slot_now["is_booked"] is False, "Cancelled slot must return to availability"
    print("\n[VERIFICATION] Slot has been successfully returned to available pool!")
    print("\nSIMULATION COMPLETE: All conversational guardrails and tool behaviors verified.")


if __name__ == "__main__":
    run_simulation()
