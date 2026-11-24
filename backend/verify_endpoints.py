import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from backend.app import app
from backend.store import store
from backend.tools import book_appointment_logic, cancel_appointment_logic


async def verify_endpoints():
    print("Testing backend API endpoints...")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        res = await client.get("/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print(f"PASS: /api/health -> {res.json()}")

        # 2. Doctors overview
        res = await client.get("/api/doctors")
        assert res.status_code == 200, f"/api/doctors failed: {res.text}"
        doctors = res.json()
        assert len(doctors) >= 6
        print(f"PASS: /api/doctors -> returned {len(doctors)} doctors")

        # 3. Appointments
        res = await client.get("/api/appointments")
        assert res.status_code == 200, f"/api/appointments failed: {res.text}"
        print(f"PASS: /api/appointments -> returned {len(res.json())} appointments")

        # 4. SSE Stream and Event Emission
        print("Testing /api/events SSE stream...")
        sse_received = []

        async def listen_sse():
            async with client.stream("GET", "/api/events") as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[len("data: "):].strip()
                        try:
                            parsed = json.loads(data_str)
                            sse_received.append(parsed)
                            if len(sse_received) >= 2:
                                break
                        except Exception:
                            pass

        listener_task = asyncio.create_task(listen_sse())

        # Give listener a moment to connect
        await asyncio.sleep(0.1)

        # Trigger a booking to produce an event
        first_doc = doctors[0]
        # find a free slot
        date_key = list(first_doc["free_slots_by_date"].keys())[0]
        slot = first_doc["free_slots_by_date"][date_key][0]

        book_res = book_appointment_logic(
            doctor_id=first_doc["id"],
            slot_id=slot["slot_id"],
            patient_name="SSE Test Patient",
            phone_number="9876543210",
            phone_confirmed=True,
        )
        assert book_res["ok"] is True

        # Wait for listener to receive the event
        await asyncio.wait_for(listener_task, timeout=5.0)

        assert len(sse_received) >= 2  # initial ping + appointment_booked
        types = [e.get("type", e.get("status")) for e in sse_received]
        print(f"PASS: /api/events -> received live events: {types}")

        # Cancel appointment to clean up
        cancel_appointment_logic(
            phone_number="9876543210",
            phone_confirmed=True,
            appointment_id=book_res["appointment"]["appointment_id"],
        )

    print("\nALL BACKEND ENDPOINTS AND SSE STREAM VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(verify_endpoints())
