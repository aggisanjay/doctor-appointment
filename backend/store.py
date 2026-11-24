import datetime
import threading
import uuid
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from backend.events import broadcaster

TIMEZONE_STR = "Asia/Kolkata"
try:
    tz = ZoneInfo(TIMEZONE_STR)
except Exception:
    tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_spoken_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parses flexible date inputs into YYYY-MM-DD string in Asia/Kolkata timezone:
    - None or empty: returns None
    - "today": today's date
    - "tomorrow": tomorrow's date
    - weekday name (e.g. "monday", "friday"): next upcoming occurrence of that day (or today if it matches)
    - "YYYY-MM-DD": valid ISO format
    """
    if not date_str:
        return None

    cleaned = date_str.strip().lower()
    now = datetime.datetime.now(tz)
    today = now.date()

    if cleaned == "today":
        return today.isoformat()
    if cleaned == "tomorrow":
        return (today + datetime.timedelta(days=1)).isoformat()

    # Check weekdays
    for wname, wday in WEEKDAYS.items():
        if wname in cleaned:
            # Days ahead (0 to 6)
            days_ahead = (wday - today.weekday()) % 7
            if days_ahead == 0 and "next" in cleaned:
                days_ahead = 7
            target = today + datetime.timedelta(days=days_ahead)
            return target.isoformat()

    # Try ISO YYYY-MM-DD
    try:
        parsed = datetime.date.fromisoformat(cleaned)
        return parsed.isoformat()
    except ValueError:
        pass

    # Try common formats like DD-MM-YYYY or DD/MM/YYYY
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            parsed = datetime.datetime.strptime(cleaned, fmt).date()
            return parsed.isoformat()
        except ValueError:
            continue

    return None


class AppointmentStore:
    """Thread-safe store for doctors, availability slots, and patient appointments."""

    def __init__(self):
        self._lock = threading.RLock()
        self.doctors: Dict[str, Dict[str, Any]] = {}
        self.slots: Dict[str, Dict[str, Any]] = {}  # slot_id -> slot_info
        self.appointments: Dict[str, Dict[str, Any]] = {}  # appointment_id -> appointment_info
        self._appointment_counter = 1000
        self.seed_data()

    def seed_data(self):
        """Seeds initial doctors (6+ across 4+ specialities) and 5 days of 30m slots."""
        with self._lock:
            self.doctors.clear()
            self.slots.clear()
            self.appointments.clear()

            doctors_meta = [
                {
                    "id": "doc_sharma",
                    "name": "Dr. Aarav Sharma",
                    "speciality": "General Physician",
                    "experience": "12 years",
                    "room": "Room 101, Ground Floor",
                },
                {
                    "id": "doc_iyer",
                    "name": "Dr. Priya Iyer",
                    "speciality": "Cardiology",
                    "experience": "15 years",
                    "room": "Room 204, Second Floor",
                },
                {
                    "id": "doc_menon",
                    "name": "Dr. Rajesh Menon",
                    "speciality": "Cardiology",
                    "experience": "10 years",
                    "room": "Room 205, Second Floor",
                },
                {
                    "id": "doc_kapoor",
                    "name": "Dr. Ananya Kapoor",
                    "speciality": "Dermatology",
                    "experience": "8 years",
                    "room": "Room 302, Third Floor",
                },
                {
                    "id": "doc_verma",
                    "name": "Dr. Vikram Verma",
                    "speciality": "Paediatrics",
                    "experience": "14 years",
                    "room": "Room 108, Ground Floor",
                },
                {
                    "id": "doc_gupta",
                    "name": "Dr. Neha Gupta",
                    "speciality": "Paediatrics",
                    "experience": "9 years",
                    "room": "Room 109, Ground Floor",
                },
                {
                    "id": "doc_patel",
                    "name": "Dr. Rohan Patel",
                    "speciality": "Orthopaedics",
                    "experience": "11 years",
                    "room": "Room 210, Second Floor",
                },
            ]

            today = datetime.datetime.now(tz).date()
            time_slots = [
                "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
                "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
            ]

            for doc in doctors_meta:
                self.doctors[doc["id"]] = doc

                # Generate slots for next 5 days
                for day_offset in range(5):
                    slot_date = (today + datetime.timedelta(days=day_offset)).isoformat()
                    for time_str in time_slots:
                        clean_date = slot_date.replace("-", "")
                        clean_time = time_str.replace(":", "")
                        slot_id = f"{doc['id']}_{clean_date}_{clean_time}"

                        self.slots[slot_id] = {
                            "slot_id": slot_id,
                            "doctor_id": doc["id"],
                            "doctor_name": doc["name"],
                            "speciality": doc["speciality"],
                            "date": slot_date,
                            "time": time_str,
                            "is_booked": False,
                        }

    def get_doctors_overview(self) -> List[Dict[str, Any]]:
        """Returns all doctors with their free slots grouped by date."""
        with self._lock:
            result = []
            for doc_id, doc in self.doctors.items():
                doc_slots = [
                    s for s in self.slots.values()
                    if s["doctor_id"] == doc_id and not s["is_booked"]
                ]
                # Group by date
                grouped: Dict[str, List[Dict[str, str]]] = {}
                for s in sorted(doc_slots, key=lambda x: (x["date"], x["time"])):
                    d = s["date"]
                    if d not in grouped:
                        grouped[d] = []
                    grouped[d].append({"slot_id": s["slot_id"], "time": s["time"]})

                result.append({
                    "id": doc["id"],
                    "name": doc["name"],
                    "speciality": doc["speciality"],
                    "experience": doc["experience"],
                    "room": doc["room"],
                    "free_slots_by_date": grouped,
                    "total_free_slots": len(doc_slots),
                })
            return result

    def get_all_appointments(self) -> List[Dict[str, Any]]:
        """Returns all appointments (active and cancelled)."""
        with self._lock:
            return sorted(
                list(self.appointments.values()),
                key=lambda x: x.get("created_at", ""),
                reverse=True,
            )

    def check_availability(
        self,
        doctor_name: Optional[str] = None,
        speciality: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Queries availability. Returns matching doctors with up to 6 free slots each.
        If no exact match, returns nearby alternatives.
        """
        with self._lock:
            parsed_date = parse_spoken_date(date)
            doc_query = doctor_name.strip().lower() if doctor_name else None
            spec_query = speciality.strip().lower() if speciality else None

            # Filter doctors
            matched_doctors = []
            for doc in self.doctors.values():
                d_name = doc["name"].lower()
                d_spec = doc["speciality"].lower()

                name_match = (doc_query is None) or (doc_query in d_name) or (d_name in doc_query)
                spec_match = (spec_query is None) or (spec_query in d_spec) or (d_spec in spec_query)

                if name_match and spec_match:
                    matched_doctors.append(doc)

            is_alternative = False
            notes = ""

            # If no doctor matched by name/speciality, fallback to all doctors or match by speciality
            if not matched_doctors:
                is_alternative = True
                matched_doctors = list(self.doctors.values())[:3]
                notes = "No exact doctor or speciality match found. Showing available options across our team."

            # Collect free slots for matched doctors
            results = []
            for doc in matched_doctors:
                free_slots = [
                    s for s in self.slots.values()
                    if s["doctor_id"] == doc["id"]
                    and not s["is_booked"]
                    and (parsed_date is None or s["date"] == parsed_date)
                ]
                free_slots.sort(key=lambda x: (x["date"], x["time"]))

                # If no free slots on requested date, check alternative dates for this doctor
                if not free_slots and parsed_date:
                    alt_slots = [
                        s for s in self.slots.values()
                        if s["doctor_id"] == doc["id"] and not s["is_booked"]
                    ]
                    alt_slots.sort(key=lambda x: (x["date"], x["time"]))
                    if alt_slots:
                        is_alternative = True
                        notes = f"No slots found on {parsed_date}. Suggesting nearest available dates."
                        free_slots = alt_slots[:6]

                if free_slots:
                    results.append({
                        "doctor_id": doc["id"],
                        "doctor_name": doc["name"],
                        "speciality": doc["speciality"],
                        "room": doc["room"],
                        "slots": [
                            {"slot_id": s["slot_id"], "date": s["date"], "time": s["time"]}
                            for s in free_slots[:6]
                        ],
                    })

            payload = {
                "ok": True,
                "is_alternative": is_alternative,
                "notes": notes,
                "matches": results,
            }

            # Broadcast SSE event
            broadcaster.broadcast("availability_checked", payload)
            return payload

    def book_appointment(
        self,
        doctor_id: str,
        slot_id: str,
        patient_name: str,
        phone_number: str,
        phone_confirmed: bool,
    ) -> Dict[str, Any]:
        """
        Books an appointment. Enforces phone confirmation, slot availability, and duplicate checks.
        """
        with self._lock:
            if not phone_confirmed:
                return {
                    "ok": False,
                    "error": "Phone number was not confirmed. Please read the number back and receive explicit confirmation before booking.",
                }

            if not patient_name or not str(patient_name).strip():
                return {
                    "ok": False,
                    "error": "Patient name is required to book an appointment.",
                }

            # Validate doctor
            doctor = self.doctors.get(doctor_id)
            if not doctor:
                return {
                    "ok": False,
                    "error": f"Doctor with ID '{doctor_id}' does not exist.",
                }

            # Validate slot
            slot = self.slots.get(slot_id)
            if not slot:
                return {
                    "ok": False,
                    "error": f"Slot '{slot_id}' not found.",
                }

            if slot["is_booked"]:
                return {
                    "ok": False,
                    "error": f"Slot on {slot['date']} at {slot['time']} is already booked. Please choose another time.",
                }

            # Check if this patient already has an active appointment with the same doctor on the same date/time
            for apt in self.appointments.values():
                if (
                    apt["status"] == "active"
                    and apt["phone_number"] == phone_number
                    and apt["doctor_id"] == doctor_id
                    and apt["date"] == slot["date"]
                    and apt["time"] == slot["time"]
                ):
                    return {
                        "ok": False,
                        "error": f"You already have an active appointment with {doctor['name']} on {slot['date']} at {slot['time']}.",
                    }

            # Perform booking
            slot["is_booked"] = True
            self._appointment_counter += 1
            apt_id = f"APT-{self._appointment_counter}"
            now_iso = datetime.datetime.now(tz).isoformat()

            appointment = {
                "appointment_id": apt_id,
                "doctor_id": doctor_id,
                "doctor_name": doctor["name"],
                "speciality": doctor["speciality"],
                "room": doctor["room"],
                "slot_id": slot_id,
                "date": slot["date"],
                "time": slot["time"],
                "patient_name": patient_name.strip(),
                "phone_number": phone_number,
                "status": "active",
                "created_at": now_iso,
            }

            self.appointments[apt_id] = appointment

            payload = {
                "ok": True,
                "appointment": appointment,
                "message": f"Appointment booked successfully with {doctor['name']} on {slot['date']} at {slot['time']}.",
            }

            # Broadcast SSE event
            broadcaster.broadcast("appointment_booked", payload)
            return payload

    def cancel_appointment(
        self,
        phone_number: str,
        phone_confirmed: bool,
        appointment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Cancels an appointment for a confirmed phone number.
        Restores slot to availability.
        """
        with self._lock:
            if not phone_confirmed:
                return {
                    "ok": False,
                    "error": "Phone number was not confirmed. Please read the number back and receive explicit confirmation before cancelling.",
                }

            # Find active appointments for this phone number
            user_active_apts = [
                apt for apt in self.appointments.values()
                if apt["phone_number"] == phone_number and apt["status"] == "active"
            ]

            if not user_active_apts:
                return {
                    "ok": False,
                    "error": f"No active appointments found for phone number ending in {phone_number[-4:]}.",
                }

            # Disambiguation needed if multiple active appointments and no ID specified
            if len(user_active_apts) > 1 and not appointment_id:
                return {
                    "ok": False,
                    "needs_disambiguation": True,
                    "appointments": [
                        {
                            "appointment_id": a["appointment_id"],
                            "doctor_name": a["doctor_name"],
                            "date": a["date"],
                            "time": a["time"],
                        }
                        for a in user_active_apts
                    ],
                    "error": f"Found {len(user_active_apts)} active appointments. Please specify which appointment to cancel by date or doctor.",
                }

            # Target appointment
            target_apt = None
            if appointment_id:
                for a in user_active_apts:
                    if a["appointment_id"].lower() == appointment_id.strip().lower():
                        target_apt = a
                        break
                if not target_apt:
                    return {
                        "ok": False,
                        "error": f"Appointment '{appointment_id}' does not exist or does not belong to your phone number.",
                    }
            else:
                target_apt = user_active_apts[0]

            # Mark cancelled
            target_apt["status"] = "cancelled"
            target_apt["cancelled_at"] = datetime.datetime.now(tz).isoformat()

            # Restore slot
            slot_id = target_apt["slot_id"]
            if slot_id in self.slots:
                self.slots[slot_id]["is_booked"] = False

            payload = {
                "ok": True,
                "appointment_id": target_apt["appointment_id"],
                "doctor_name": target_apt["doctor_name"],
                "date": target_apt["date"],
                "time": target_apt["time"],
                "message": f"Appointment with {target_apt['doctor_name']} on {target_apt['date']} at {target_apt['time']} has been cancelled.",
            }

            # Broadcast SSE event
            broadcaster.broadcast("appointment_cancelled", payload)
            return payload


# Global singleton instance
store = AppointmentStore()
