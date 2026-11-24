import React from "react";
import type { Appointment } from "../types";

interface AppointmentsTableProps {
  appointments: Appointment[];
  highlightedAptId: string | null;
  isLoading: boolean;
}

export const AppointmentsTable: React.FC<AppointmentsTableProps> = ({
  appointments,
  highlightedAptId,
  isLoading,
}) => {
  const maskPhone = (phone: string) => {
    if (!phone) return "—";
    const clean = phone.replace(/\D/g, "");
    if (clean.length >= 4) {
      return "••••••" + clean.slice(-4);
    }
    return phone;
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr + "T00:00:00");
      return d.toLocaleDateString("en-IN", {
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="card-panel">
      <div className="panel-header-row">
        <div>
          <h2 className="panel-title">Appointments</h2>
          <p className="panel-caption">Live updates from voice assistant</p>
        </div>
        <span className="count-pill">
          {appointments.length} total
        </span>
      </div>

      {isLoading ? (
        <div className="panel-loading">
          <div className="loading-spinner" />
          <p>Loading appointments...</p>
        </div>
      ) : appointments.length === 0 ? (
        <div className="empty-state">
          <p className="empty-title">No appointments yet</p>
          <p className="empty-subtitle">
            Bookings made during the voice call will appear here in real time.
          </p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="appointments-table">
            <thead>
              <tr>
                <th scope="col">ID</th>
                <th scope="col">Patient</th>
                <th scope="col">Phone</th>
                <th scope="col">Doctor</th>
                <th scope="col">Date</th>
                <th scope="col">Time</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {appointments.map((apt) => {
                const isHighlighted = apt.appointment_id === highlightedAptId;
                const isCancelled = apt.status === "cancelled";

                return (
                  <tr
                    key={apt.appointment_id}
                    className={`table-row ${isHighlighted ? "row-highlight" : ""} ${isCancelled ? "row-cancelled" : ""}`}
                  >
                    <td className="mono-text apt-id">{apt.appointment_id}</td>
                    <td className="patient-name">{apt.patient_name}</td>
                    <td className="mono-text phone-masked">{maskPhone(apt.phone_number)}</td>
                    <td className="doctor-cell">
                      <div className="doc-main">{apt.doctor_name}</div>
                      <div className="doc-sub">{apt.speciality}</div>
                    </td>
                    <td className="mono-text">{formatDate(apt.date)}</td>
                    <td className="mono-text time-cell">{apt.time}</td>
                    <td>
                      <span className={`status-tag ${apt.status}`}>
                        {apt.status === "active" ? "Confirmed" : "Cancelled"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
