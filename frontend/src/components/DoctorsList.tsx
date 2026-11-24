import React, { useState } from "react";
import type { Doctor } from "../types";
import { Clock, MapPin, Award } from "lucide-react";

interface DoctorsListProps {
  doctors: Doctor[];
  isLoading: boolean;
  error: string | null;
}

export const DoctorsList: React.FC<DoctorsListProps> = ({
  doctors,
  isLoading,
  error,
}) => {
  const [selectedSpeciality, setSelectedSpeciality] = useState<string>("all");

  const specialities = [
    "all",
    ...Array.from(new Set(doctors.map((d) => d.speciality))),
  ];

  const filteredDoctors =
    selectedSpeciality === "all"
      ? doctors
      : doctors.filter((d) => d.speciality === selectedSpeciality);

  const formatDateLabel = (dateStr: string) => {
    try {
      const date = new Date(dateStr + "T00:00:00");
      return date.toLocaleDateString("en-IN", {
        weekday: "short",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  if (isLoading) {
    return (
      <div className="card-panel">
        <h2 className="panel-title">Doctors & Available Slots</h2>
        <div className="panel-loading">
          <div className="loading-spinner" />
          <p>Loading schedule...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-panel">
        <h2 className="panel-title">Doctors & Available Slots</h2>
        <div className="panel-error">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card-panel">
      <div className="panel-header-row">
        <div>
          <h2 className="panel-title">Doctors & Available Slots</h2>
          <p className="panel-caption">Real-time availability for the next 5 days</p>
        </div>

        {/* Speciality filter pills */}
        <div className="speciality-filter" role="tablist" aria-label="Filter by speciality">
          {specialities.map((spec) => (
            <button
              key={spec}
              role="tab"
              aria-selected={selectedSpeciality === spec}
              className={`filter-chip ${selectedSpeciality === spec ? "active" : ""}`}
              onClick={() => setSelectedSpeciality(spec)}
            >
              {spec === "all" ? "All Specialties" : spec}
            </button>
          ))}
        </div>
      </div>

      <div className="doctors-grid">
        {filteredDoctors.map((doc) => {
          const dates = Object.keys(doc.free_slots_by_date).sort();

          return (
            <div key={doc.id} className="doctor-card">
              <div className="doctor-header">
                <div>
                  <h3 className="doctor-name">{doc.name}</h3>
                  <span className="doctor-spec-tag">{doc.speciality}</span>
                </div>
                <div className="slots-badge">
                  <span className="slots-count">{doc.total_free_slots}</span>
                  <span className="slots-label">free</span>
                </div>
              </div>

              <div className="doctor-meta">
                <span className="meta-item">
                  <MapPin size={13} aria-hidden="true" />
                  <span>{doc.room}</span>
                </span>
                <span className="meta-item">
                  <Award size={13} aria-hidden="true" />
                  <span>{doc.experience}</span>
                </span>
              </div>

              <div className="schedule-section">
                {dates.length === 0 ? (
                  <p className="no-slots">No slots available</p>
                ) : (
                  dates.map((dateStr) => {
                    const slots = doc.free_slots_by_date[dateStr];
                    if (!slots || slots.length === 0) return null;

                    return (
                      <div key={dateStr} className="day-schedule-group">
                        <div className="day-label">{formatDateLabel(dateStr)}</div>
                        <div className="chips-container">
                          {slots.slice(0, 6).map((s) => (
                            <span key={s.slot_id} className="time-chip">
                              <Clock size={11} aria-hidden="true" />
                              <span className="mono-time">{s.time}</span>
                            </span>
                          ))}
                          {slots.length > 6 && (
                            <span className="more-chips">+{slots.length - 6} more</span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
