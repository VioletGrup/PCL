import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import "./Parameters.css";

import pclLogo from "../assets/logos/pcllogo.png";
import backgroundImage from "../assets/logos/Australia-Office-2025.png";

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
  const [minPileReveal, setMinPileReveal] = useState(""); // m
  const [maxPileReveal, setMaxPileReveal] = useState(""); // m
  const [installationTolerance, setInstallationTolerance] = useState(""); // m

  // ✅ NEW (Flat + XTR)
  const [trackerEdgeOverhang, setTrackerEdgeOverhang] = useState(""); // m

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

        // ✅ restore new field
        setTrackerEdgeOverhang(saved.trackerEdgeOverhang ?? "");

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

  function validateRequired() {
    // Shared required
    if (
      !maxIncline ||
      !minPileReveal ||
      !maxPileReveal ||
      !installationTolerance ||
      !trackerEdgeOverhang
    ) {
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

      // ✅ New shared field
      trackerEdgeOverhang,

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
    <div className="pr-shell">
      {/* Background */}
      <div className="pr-bg" aria-hidden="true">
        <img src={backgroundImage} alt="" className="pr-bgImg" />
        <div className="pr-bgOverlay" />
        <div className="pr-gridOverlay" />
      </div>

      {/* Header */}
      <header className="pr-header">
        <div className="pr-headerInner">
          <div className="pr-brand">
            <img src={pclLogo} alt="PCL Logo" className="pr-logo" />
            <div className="pr-brandText">
              <div className="pr-brandTitle">Earthworks Analysis Tool</div>
              <div className="pr-brandSub">Parameters → Run</div>
            </div>
          </div>

          <div className="pr-headerActions">
            <Link to="/review" className="pr-navLink">
              ← Back
            </Link>

            <div className="pr-stepPill">
              <span className="pr-stepDot" />
              Step 3 of 3
            </div>

            <button className="pr-btn pr-btnPrimary" onClick={proceed}>
              Run Analysis →
            </button>
          </div>
        </div>
      </header>

      {/* Scroll area */}
      <div className="pr-mainScroll">
        <main className="pr-main">
          {/* Hero */}
          <div className="pr-hero">
            <div className="pr-badge">
              <span className="pr-badgeDot" />
              Project Setup
            </div>

            <h1 className="pr-h1">Project Parameters</h1>

            <p className="pr-subtitle">
              Enter tracker limits and installation tolerances. These values are saved locally and
              passed into the analysis step.
            </p>

            <div className="pr-metaCard">
              <div className="pr-metaRow">
                <div className="pr-metaLabel">File</div>
                <div className="pr-metaValue">{fileName || "—"}</div>
              </div>

              <div className="pr-metaGrid">
                <div className="pr-metaItem">
                  <div className="pr-miniLabel">Sheet</div>
                  <div className="pr-miniValue">{sheetName || "—"}</div>
                </div>

                <div className="pr-metaItem">
                  <div className="pr-miniLabel">Rows</div>
                  <div className="pr-miniValue">{rowCount || 0}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Tracker type */}
          <section className="pr-card">
            <div className="pr-cardHead pr-cardHeadTight">
              <div>
                <h2 className="pr-cardTitle">Tracker Type</h2>
                <p className="pr-cardSub">
                  This determines which inputs are required and which analysis path is run.
                </p>
              </div>

              <div className="pr-pill">
                <span className="pr-pillDot" />
                Required inputs
              </div>
            </div>

            <div className="pr-toggleRow">
              <button
                className={`pr-toggleBtn ${trackerType === "flat" ? "is-active" : ""}`}
                onClick={() => setTrackerType("flat")}
                type="button"
              >
                Flat Tracker
              </button>

              <button
                className={`pr-toggleBtn ${trackerType === "xtr" ? "is-active" : ""}`}
                onClick={() => setTrackerType("xtr")}
                type="button"
              >
                XTR
              </button>
            </div>

            <div className="pr-note">
              Required fields:{" "}
              <strong>
                {trackerType === "xtr"
                  ? "Max incline, Min/Max pile reveal, Tracker edge overhang, Max segment slope change, Max cumulative slope change, Installation tolerance"
                  : "Max incline, Min/Max pile reveal, Tracker edge overhang, Installation tolerance"}
              </strong>
            </div>
          </section>

          {/* Manufacturer */}
          <section className="pr-card">
            <div className="pr-cardHead pr-cardHeadTight">
              <div>
                <h2 className="pr-cardTitle">Manufacturer</h2>
                <p className="pr-cardSub">
                  Selecting a manufacturer will auto-fill parameters in a future update.
                </p>
              </div>
            </div>

            <select
              className="pr-select"
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
          <section className="pr-card">
            <div className="pr-cardHead">
              <div>
                <h2 className="pr-cardTitle">
                  {trackerType === "xtr" ? "XTR Parameters" : "Flat Tracker Parameters"}
                </h2>
                <p className="pr-cardSub">All fields in this section are required.</p>
              </div>
            </div>

            <div className="pr-formGrid">
              <div className="pr-field">
                <label className="pr-label">Maximum incline (%)</label>
                <input
                  className="pr-input"
                  type="number"
                  value={maxIncline}
                  onChange={(e) => setMaxIncline(e.target.value)}
                  placeholder="e.g., 15"
                />
              </div>

              <div className="pr-field">
                <label className="pr-label">Minimum pile reveal height (m)</label>
                <input
                  className="pr-input"
                  type="number"
                  value={minPileReveal}
                  onChange={(e) => setMinPileReveal(e.target.value)}
                  placeholder="e.g., 1.2"
                />
              </div>

              <div className="pr-field">
                <label className="pr-label">Maximum pile reveal height (m)</label>
                <input
                  className="pr-input"
                  type="number"
                  value={maxPileReveal}
                  onChange={(e) => setMaxPileReveal(e.target.value)}
                  placeholder="e.g., 3.2"
                />
              </div>

              {/* ✅ NEW shared parameter */}
              <div className="pr-field">
                <label className="pr-label">Tracker edge overhang (m)</label>
                <input
                  className="pr-input"
                  type="number"
                  value={trackerEdgeOverhang}
                  onChange={(e) => setTrackerEdgeOverhang(e.target.value)}
                  placeholder="e.g., 0.5"
                />
                <div className="pr-hint">
                  Horizontal overhang beyond the outermost pile/torque tube reference (project-specific).
                </div>
              </div>

              {/* XTR-only */}
              {trackerType === "xtr" && (
                <>
                  <div className="pr-field">
                    <label className="pr-label">Max segment slope change (%)</label>
                    <input
                      className="pr-input"
                      type="number"
                      value={maxSegmentSlopeChange}
                      onChange={(e) => setMaxSegmentSlopeChange(e.target.value)}
                      placeholder="e.g., 1.0"
                    />
                    <div className="pr-hint">Maximum change in slope between adjacent segments.</div>
                  </div>

                  <div className="pr-field">
                    <label className="pr-label">Max cumulative slope change (%)</label>
                    <input
                      className="pr-input"
                      type="number"
                      value={maxCumulativeSlopeChange}
                      onChange={(e) => setMaxCumulativeSlopeChange(e.target.value)}
                      placeholder="e.g., 3.0"
                    />
                    <div className="pr-hint">
                      Maximum cumulative slope change along the torque tube.
                    </div>
                  </div>
                </>
              )}
            </div>
          </section>

          {/* Installation tolerances */}
          <section className="pr-card">
            <div className="pr-cardHead">
              <div>
                <h2 className="pr-cardTitle">Installation Tolerances</h2>
                <p className="pr-cardSub">
                  Often a single value split between min and max reveal allowances (varies by project).
                </p>
              </div>
            </div>

            <div className="pr-field pr-fieldSingle">
              <label className="pr-label">Total installation tolerance (m)</label>
              <input
                className="pr-input"
                type="number"
                value={installationTolerance}
                onChange={(e) => setInstallationTolerance(e.target.value)}
                placeholder="e.g., 0.2"
              />
              {halfTolerance !== null && (
                <div className="pr-hint">
                  Split suggestion: <strong>{halfTolerance}</strong> m to min +{" "}
                  <strong>{halfTolerance}</strong> m to max.
                </div>
              )}
            </div>
          </section>

          {error && <div className="pr-alert pr-alertError">{error}</div>}

          <div className="pr-actions">
            <Link to="/review" className="pr-navLink">
              ← Back
            </Link>

            <button className="pr-btn pr-btnPrimary" onClick={proceed}>
              Run Analysis →
            </button>
          </div>
        </main>

        <footer className="pr-footer">
          <span className="pr-footerMuted">PCL Earthworks Tool • Upload → Review → Parameters</span>
        </footer>
      </div>
    </div>
  );
}
