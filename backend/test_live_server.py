import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx

BASE_URL = "http://127.0.0.1:8000"


async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Health
        print("[1] Testing GET /api/health...")
        res = await client.get(f"{BASE_URL}/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print(f"    Status: {res.status_code}, Body: {res.json()}")

        # 2. Doctors
        print("[2] Testing GET /api/doctors...")
        res = await client.get(f"{BASE_URL}/api/doctors")
        assert res.status_code == 200, f"Doctors check failed: {res.text}"
        doctors = res.json()
        print(f"    Status: {res.status_code}, Total doctors: {len(doctors)}")
        first_doc = doctors[0]
        first_date = list(first_doc["free_slots_by_date"].keys())[0]
        first_slot = first_doc["free_slots_by_date"][first_date][0]

        # 3. Appointments
        print("[3] Testing GET /api/appointments...")
        res = await client.get(f"{BASE_URL}/api/appointments")
        assert res.status_code == 200
        print(f"    Status: {res.status_code}, Total appointments: {len(res.json())}")

        # 4. SSE Stream + Event Verification
        print("[4] Testing GET /api/events SSE stream...")
        received_events = []

        async def listen_sse():
            async with client.stream("GET", f"{BASE_URL}/api/events") as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[len("data: "):].strip()
                        try:
                            payload = json.loads(data)
                            event_type = payload.get("type") or payload.get("status")
                            print(f"    SSE Event received: {event_type}")
                            received_events.append(payload)
                            if len(received_events) >= 2:
                                break
                        except Exception:
                            pass

        listener = asyncio.create_task(listen_sse())
        await asyncio.sleep(0.5)

        # Trigger booking action via HTTP POST to the running server
        print("    Triggering tool via POST /api/test/action: book_appointment...")
        book_res = await client.post(
            f"{BASE_URL}/api/test/action",
            json={
                "action": "book_appointment",
                "params": {
                    "doctor_id": first_doc["id"],
                    "slot_id": first_slot["slot_id"],
                    "patient_name": "Live SSE Test Patient",
                    "phone_number": "9876543210",
                    "phone_confirmed": True,
                },
            },
        )
        assert book_res.status_code == 200, f"Booking failed: {book_res.text}"
        book_data = book_res.json()
        assert book_data["ok"] is True
        apt_id = book_data["appointment"]["appointment_id"]
        print(f"    Booking success: {apt_id}")

        await asyncio.wait_for(listener, timeout=5.0)
        assert len(received_events) >= 2
        print(f"    PASS: SSE stream received {len(received_events)} events successfully.")

        # Clean up by cancelling
        cancel_res = await client.post(
            f"{BASE_URL}/api/test/action",
            json={
                "action": "cancel_appointment",
                "params": {
                    "phone_number": "9876543210",
                    "phone_confirmed": True,
                    "appointment_id": apt_id,
                },
            },
        )
        assert cancel_res.status_code == 200
        print(f"    PASS: Cleaned up test appointment via cancel tool.")

    print("\nALL SERVER ENDPOINTS AND LIVE SSE EMISSION VERIFIED AGAINST RUNNING SERVER!")


if __name__ == "__main__":
    asyncio.run(main())
