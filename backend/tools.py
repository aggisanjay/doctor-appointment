import logging
from typing import Any, Dict, Optional

from pipecat.adapters.llm.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams

from backend.phone import normalize_phone_number
from backend.store import store

logger = logging.getLogger("appointment_tools")
logger.setLevel(logging.INFO)


def check_doctor_availability_logic(
    doctor_name: Optional[str] = None,
    speciality: Optional[str] = None,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Business logic for checking doctor availability."""
    logger.info(
        f"TOOL CALL: check_doctor_availability(doctor_name={doctor_name}, speciality={speciality}, date={date})"
    )
    try:
        res = store.check_availability(
            doctor_name=doctor_name, speciality=speciality, date=date
        )
        logger.info(f"TOOL RESULT: check_doctor_availability -> {res.get('ok')} ({len(res.get('matches', []))} doctors found)")
        return res
    except Exception as e:
        logger.error(f"Error in check_doctor_availability: {e}", exc_info=True)
        return {"ok": False, "error": f"Failed to check doctor availability: {str(e)}"}


def book_appointment_logic(
    doctor_id: str,
    slot_id: str,
    patient_name: str,
    phone_number: str,
    phone_confirmed: bool,
) -> Dict[str, Any]:
    """Business logic for booking an appointment."""
    logger.info(
        f"TOOL CALL: book_appointment(doctor_id={doctor_id}, slot_id={slot_id}, patient={patient_name}, phone={phone_number}, confirmed={phone_confirmed})"
    )

    # 1. Enforce phone confirmation rule in code
    if not phone_confirmed:
        logger.warning("REJECTED book_appointment: phone_confirmed is False")
        return {
            "ok": False,
            "error": "The caller's phone number was not explicitly confirmed. You must read back the phone number digit by digit and receive a 'yes' before booking.",
        }

    # 2. Normalize and validate phone number in code
    is_valid, norm_phone, err_msg = normalize_phone_number(phone_number)
    if not is_valid:
        logger.warning(f"REJECTED book_appointment: invalid phone '{phone_number}' -> {err_msg}")
        return {
            "ok": False,
            "error": f"Invalid phone number '{phone_number}'. {err_msg}",
        }

    # 3. Call store to book
    res = store.book_appointment(
        doctor_id=doctor_id,
        slot_id=slot_id,
        patient_name=patient_name,
        phone_number=norm_phone,
        phone_confirmed=phone_confirmed,
    )
    logger.info(f"TOOL RESULT: book_appointment -> {res.get('ok')}")
    return res


def cancel_appointment_logic(
    phone_number: str,
    phone_confirmed: bool,
    appointment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Business logic for cancelling an appointment."""
    logger.info(
        f"TOOL CALL: cancel_appointment(phone={phone_number}, confirmed={phone_confirmed}, apt_id={appointment_id})"
    )

    # 1. Enforce phone confirmation rule in code
    if not phone_confirmed:
        logger.warning("REJECTED cancel_appointment: phone_confirmed is False")
        return {
            "ok": False,
            "error": "The caller's phone number was not explicitly confirmed. You must read back the phone number and receive a 'yes' before cancelling.",
        }

    # 2. Normalize and validate phone number in code
    is_valid, norm_phone, err_msg = normalize_phone_number(phone_number)
    if not is_valid:
        logger.warning(f"REJECTED cancel_appointment: invalid phone '{phone_number}' -> {err_msg}")
        return {
            "ok": False,
            "error": f"Invalid phone number '{phone_number}'. {err_msg}",
        }

    # 3. Call store to cancel
    res = store.cancel_appointment(
        phone_number=norm_phone,
        phone_confirmed=phone_confirmed,
        appointment_id=appointment_id,
    )
    logger.info(f"TOOL RESULT: cancel_appointment -> {res.get('ok')}")
    return res


from pipecat.services.llm_service import FunctionCallResultProperties

# Pipecat Async Handlers
async def pipecat_check_doctor_availability(params: FunctionCallParams):
    args = params.arguments or {}
    doctor_name = args.get("doctor_name")
    speciality = args.get("speciality")
    date = args.get("date")

    result = check_doctor_availability_logic(
        doctor_name=doctor_name, speciality=speciality, date=date
    )
    await params.result_callback(
        result, properties=FunctionCallResultProperties(run_llm=True)
    )


async def pipecat_book_appointment(params: FunctionCallParams):
    args = params.arguments or {}
    doctor_id = args.get("doctor_id")
    slot_id = args.get("slot_id")
    patient_name = args.get("patient_name")
    phone_number = str(args.get("phone_number", ""))
    phone_confirmed = bool(args.get("phone_confirmed", False))

    result = book_appointment_logic(
        doctor_id=doctor_id,
        slot_id=slot_id,
        patient_name=patient_name,
        phone_number=phone_number,
        phone_confirmed=phone_confirmed,
    )
    await params.result_callback(
        result, properties=FunctionCallResultProperties(run_llm=True)
    )


async def pipecat_cancel_appointment(params: FunctionCallParams):
    args = params.arguments or {}
    phone_number = str(args.get("phone_number", ""))
    phone_confirmed = bool(args.get("phone_confirmed", False))
    appointment_id = args.get("appointment_id")

    result = cancel_appointment_logic(
        phone_number=phone_number,
        phone_confirmed=phone_confirmed,
        appointment_id=appointment_id,
    )
    await params.result_callback(
        result, properties=FunctionCallResultProperties(run_llm=True)
    )


# Tool schemas for Pipecat LLM registration
CHECK_AVAILABILITY_SCHEMA = FunctionSchema(
    name="check_doctor_availability",
    description="Check doctor availability and available appointment slots. Returns matching doctors with up to 6 free slots each. If no exact match, returns nearby alternatives.",
    properties={
        "doctor_name": {
            "type": "string",
            "description": "Optional name of the doctor (e.g. 'Dr. Sharma' or 'Aarav').",
        },
        "speciality": {
            "type": "string",
            "description": "Optional medical speciality (e.g. 'Cardiology', 'Dermatology', 'General Physician', 'Paediatrics', 'Orthopaedics').",
        },
        "date": {
            "type": "string",
            "description": "Preferred date. Accepts 'today', 'tomorrow', day of week (e.g. 'Monday', 'Friday'), or YYYY-MM-DD.",
        },
    },
    required=[],
    handler=pipecat_check_doctor_availability,
)

BOOK_APPOINTMENT_SCHEMA = FunctionSchema(
    name="book_appointment",
    description="Book a doctor appointment slot. MUST ONLY be called after reading back the 10-digit phone number and obtaining explicit confirmation ('yes') from the caller.",
    properties={
        "doctor_id": {
            "type": "string",
            "description": "The unique ID of the doctor (e.g. 'doc_sharma').",
        },
        "slot_id": {
            "type": "string",
            "description": "The unique ID of the selected slot (e.g. 'doc_sharma_20261125_0930').",
        },
        "patient_name": {
            "type": "string",
            "description": "The full name of the patient.",
        },
        "phone_number": {
            "type": "string",
            "description": "The 10-digit Indian mobile number of the patient spoken by the caller.",
        },
        "phone_confirmed": {
            "type": "boolean",
            "description": "Must be set to true ONLY if you read back the phone number digit by digit and the caller explicitly said 'yes'. Never set to true without explicit confirmation.",
        },
    },
    required=["doctor_id", "slot_id", "patient_name", "phone_number", "phone_confirmed"],
    handler=pipecat_book_appointment,
)

CANCEL_APPOINTMENT_SCHEMA = FunctionSchema(
    name="cancel_appointment",
    description="Cancel an existing appointment. MUST ONLY be called after reading back the phone number and obtaining explicit confirmation ('yes') from the caller.",
    properties={
        "phone_number": {
            "type": "string",
            "description": "The 10-digit Indian mobile number of the patient spoken by the caller.",
        },
        "phone_confirmed": {
            "type": "boolean",
            "description": "Must be set to true ONLY if you read back the phone number and the caller explicitly confirmed ('yes').",
        },
        "appointment_id": {
            "type": "string",
            "description": "Optional specific appointment ID (e.g. 'APT-1001') if the patient has multiple active appointments.",
        },
    },
    required=["phone_number", "phone_confirmed"],
    handler=pipecat_cancel_appointment,
)

ALL_TOOL_SCHEMAS = [
    CHECK_AVAILABILITY_SCHEMA,
    BOOK_APPOINTMENT_SCHEMA,
    CANCEL_APPOINTMENT_SCHEMA,
]
