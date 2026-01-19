import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./Parameters.css";

export default function Parameters() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const fileNameFromState = state?.fileName || "";
  const sheetNameFromState = state?.sheetName || "";
  const trackerTypeFromState = state?.trackerType || "flat";
  const rowCountFromState = Number(state?.rowCount || 0);

  const [fileName, setFileName] = useState(fileNameFromState);
  const [sheetName, setSheetName] = useState(sheetNameFromState);
  const [rowCount, setRowCount] = useState(rowCountFromState);

  // Tracker type selection
  const [trackerType, setTrackerType] = useState(trackerTypeFromState); // "flat" | "xtr"

  // Manufacturer selection (future auto-fill)
  const [manufacturer, setManufacturer] = useState("");

  // Shared fields (Flat + XTR)
  const [maxIncline, setMaxIncline] = useState(""); // %
  const [minPileReveal, setMinPileReveal] = useState(""); // mm
  const [maxPileReveal, setMaxPileReveal] = useState(""); // mm
  const [installationTolerance, setInstallationTolerance] = useState(""); // mm

  // XTR-only fields (slope change in %)
  const [maxSegmentSlopeChange, setMaxSegmentSlopeChange] = useState(""); // %
  const [maxCumulativeSlopeChange, setMaxCumulativeSlopeChange] = useState(""); // %

  const [error, setError] = useState("");

  // Refresh-safe load
  useEffect(() => {
    // Restore saved parameters
    try {
      const saved = JSON.parse(localStorage.getItem("pcl_parameters") || "null");
      if (saved) {
        setManufacturer(saved.manufacturer ?? "");
        setTrackerType(saved.trackerType ?? trackerTypeFromState);

        setMaxIncline(saved.maxIncline ?? "");
        setMinPileReveal(saved.minPileReveal ?? "");
        setMaxPileReveal(saved.maxPileReveal ?? "");
        setInstallationTolerance(saved.installationTolerance ?? "");

        setMaxSegmentSlopeChange(saved.maxSegmentSlopeChange ?? "");
        setMaxCumulativeSlopeChange(saved.maxCumulativeSlopeChange ?? "");
      }
    } catch {
      // ignore
    }

    // If state missing after refresh, recover from pcl_config & columns
    try {
      if (!fileNameFromState || !sheetNameFromState) {
        const cfg = JSON.parse(localStorage.getItem("pcl_config") || "{}");
        if (cfg?.fileName) setFileName(cfg.fileName);
        if (cfg?.sheetName) setSheetName(cfg.sheetName);
      }
      if (!rowCountFromState) {
        const poleLS = JSON.parse(localStorage.getItem("pcl_columns_pole") || "[]");
        if (Array.isArray(poleLS) && poleLS.length) setRowCount(poleLS.length);
      }
    } catch {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Helpful display (not enforced)
  const halfTolerance = useMemo(() => {
    const t = Number(installationTolerance);
    if (!Number.isFinite(t) || t <= 0) return null;
    return t / 2;
  }, [installationTolerance]);

  // When switching tracker type, clear fields that don't apply (optional but cleaner)
  useEffect(() => {
    setError("");
    if (trackerType === "flat") {
      setMaxSegmentSlopeChange("");
      setMaxCumulativeSlopeChange("");
    }
  }, [trackerType]);

  function goBack() {
    navigate("/review");
  }

  function validateRequired() {
    // Shared required
    if (!maxIncline || !minPileReveal || !maxPileReveal || !installationTolerance) {
      return "Please complete all required fields.";
    }

    // XTR required extras
    if (trackerType === "xtr") {
      if (!maxSegmentSlopeChange || !maxCumulativeSlopeChange) {
        return "Please complete all required XTR slope change fields.";
      }
    }

    // Basic numeric sanity checks
    const minPR = Number(minPileReveal);
    const maxPR = Number(maxPileReveal);
    if (Number.isFinite(minPR) && Number.isFinite(maxPR) && maxPR < minPR) {
      return "Maximum pile reveal height must be greater than or equal to minimum pile reveal height.";
    }

    return "";
  }

  function proceed() {
    const msg = validateRequired();
    if (msg) {
      setError(msg);
      return;
    }
    setError("");

    const payload = {
      fileName,
      sheetName,
      rowCount,
      trackerType,
      manufacturer,

      // Shared
      maxIncline,
      minPileReveal,
      maxPileReveal,
      installationTolerance,

      // XTR-only
      maxSegmentSlopeChange: trackerType === "xtr" ? maxSegmentSlopeChange : "",
      maxCumulativeSlopeChange: trackerType === "xtr" ? maxCumulativeSlopeChange : "",
    };

    try {
      localStorage.setItem("pcl_parameters", JSON.stringify(payload));
    } catch {
      // ignore
    }

    navigate("/run-analysis", { state: payload });
  }

  return (
    <div className="params-shell">
      {/* Top bar */}
      <header className="params-topbar">
        <div className="params-left">
          <button className="params-back" onClick={goBack}>
            ← Back
          </button>

          <div className="params-titlewrap">
            <h1 className="params-title">Project Parameters</h1>
            <div className="params-subtitle">
              Enter tracker limits and installation tolerances.
            </div>
          </div>
        </div>

        <div className="params-meta">
          <div className="meta-chip">
            <span className="meta-label">File</span>
            <span className="meta-value">{fileName || "—"}</span>
          </div>
          <div className="meta-chip">
            <span className="meta-label">Sheet</span>
            <span className="meta-value">{sheetName || "—"}</span>
          </div>
          <div className="meta-chip">
            <span className="meta-label">Rows</span>
            <span className="meta-value">{rowCount || 0}</span>
          </div>
          <div className="meta-chip">
            <span className="meta-label">Step</span>
            <span className="meta-value">3 of 3</span>
          </div>
        </div>
      </header>

      <main className="params-content">
        {/* Tracker type */}
        <section className="params-card">
          <h2 className="card-title">Tracker Type</h2>
          <p className="card-desc">
            This determines which inputs are required and which analysis path is run.
          </p>

          <div className="toggle-row">
            <button
              className={`toggle-btn ${trackerType === "flat" ? "is-active" : ""}`}
              onClick={() => setTrackerType("flat")}
              type="button"
            >
              Flat Tracker
            </button>
            <button
              className={`toggle-btn ${trackerType === "xtr" ? "is-active" : ""}`}
              onClick={() => setTrackerType("xtr")}
              type="button"
            >
              XTR
            </button>
          </div>

          <div className="small-note">
            Required fields:{" "}
            <strong>
              {trackerType === "xtr"
                ? "Max incline, Min/Max pile reveal, Max segment slope change, Max cumulative slope change, Installation tolerances"
                : "Max incline, Min/Max pile reveal, Installation tolerances"}
            </strong>
          </div>
        </section>

        {/* Manufacturer (future auto-fill) */}
        <section className="params-card">
          <h2 className="card-title">Manufacturer</h2>
          <p className="card-desc">
            Selecting a manufacturer will auto-fill parameters in a future update.
          </p>

          <select
            className="params-select"
            value={manufacturer}
            onChange={(e) => setManufacturer(e.target.value)}
          >
            <option value="">— Select manufacturer —</option>
            <option value="nextracker">Nextracker</option>
            <option value="pvh">PVH</option>
            <option value="gamechange">GameChange</option>
            <option value="ati">ATI</option>
          </select>
        </section>

        {/* Required inputs */}
        <section className="params-card">
          <h2 className="card-title">
            {trackerType === "xtr" ? "XTR Parameters" : "Flat Tracker Parameters"}
          </h2>

          <div className="form-grid">
            <div className="form-field">
              <label>Maximum incline (%)</label>
              <input
                className="params-input"
                type="number"
                value={maxIncline}
                onChange={(e) => setMaxIncline(e.target.value)}
                placeholder="e.g., 15"
              />
            </div>

            <div className="form-field">
              <label>Minimum pile reveal height (m)</label>
              <input
                className="params-input"
                type="number"
                value={minPileReveal}
                onChange={(e) => setMinPileReveal(e.target.value)}
                placeholder="e.g., 1.2"
              />
            </div>

            <div className="form-field">
              <label>Maximum pile reveal height (m)</label>
              <input
                className="params-input"
                type="number"
                value={maxPileReveal}
                onChange={(e) => setMaxPileReveal(e.target.value)}
                placeholder="e.g., 3.2"
              />
            </div>

            {/* XTR-only */}
            {trackerType === "xtr" && (
              <>
                <div className="form-field">
                  <label>Max segment slope change (%)</label>
                  <input
                    className="params-input"
                    type="number"
                    value={maxSegmentSlopeChange}
                    onChange={(e) => setMaxSegmentSlopeChange(e.target.value)}
                    placeholder="e.g., 1.0"
                  />
                  <div className="field-hint">
                    Maximum change in slope between adjacent segments.
                  </div>
                </div>

                <div className="form-field">
                  <label>Max cumulative slope change (%)</label>
                  <input
                    className="params-input"
                    type="number"
                    value={maxCumulativeSlopeChange}
                    onChange={(e) => setMaxCumulativeSlopeChange(e.target.value)}
                    placeholder="e.g., 3.0"
                  />
                  <div className="field-hint">
                    Maximum cumulative slope change along the torque tube.
                  </div>
                </div>
              </>
            )}
          </div>
        </section>

        {/* Installation tolerances */}
        <section className="params-card">
          <h2 className="card-title">Installation Tolerances</h2>
          <p className="card-desc">
            Allows for construction deviations. Often a single value (e.g., 0.2 m) split
            between the min and max reveal allowances. Do not hardcode; varies by project.
          </p>

          <div className="form-field single-field">
            <label>Total installation tolerance (m)</label>
            <input
              className="params-input"
              type="number"
              value={installationTolerance}
              onChange={(e) => setInstallationTolerance(e.target.value)}
              placeholder="e.g., 0.2"
            />
            {halfTolerance !== null && (
              <div className="field-hint">
                Split suggestion: <strong>{halfTolerance}</strong> m to min +{" "}
                <strong>{halfTolerance}</strong> m to max.
              </div>
            )}
          </div>
        </section>

        {error && <div className="params-error">{error}</div>}

        <div className="params-actions">
          <button className="btn-secondary" onClick={goBack}>
            ← Back
          </button>

          <button className="btn-primary" onClick={proceed}>
            Run Analysis →
          </button>
        </div>
      </main>

      <footer className="params-footer">
        PCL Earthworks Tool • Upload → Review → Parameters
      </footer>
    </div>
  );
}
