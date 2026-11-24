export interface SlotInfo {
  slot_id: string;
  time: string;
}

export interface Doctor {
  id: string;
  name: string;
  speciality: string;
  experience: string;
  room: string;
  free_slots_by_date: Record<string, SlotInfo[]>;
  total_free_slots: number;
}

export interface Appointment {
  appointment_id: string;
  doctor_id: string;
  doctor_name: string;
  speciality: string;
  room: string;
  slot_id: string;
  date: string;
  time: string;
  patient_name: string;
  phone_number: string;
  status: "active" | "cancelled";
  created_at: string;
  cancelled_at?: string;
}

export interface TranscriptItem {
  id: string;
  role: "user" | "bot";
  text: string;
  isFinal: boolean;
  timestamp: string;
}

export type CallState = "idle" | "ringing" | "connected" | "ended" | "error";

export interface BookingNotification {
  type: "booked" | "cancelled";
  appointment_id?: string;
  doctor_name: string;
  date: string;
  time: string;
  message?: string;
}
