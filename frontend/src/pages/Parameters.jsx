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

  const [trackerType, setTrackerType] = useState(trackerTypeFromState); // "flat" | "xtr"
  const [manufacturer, setManufacturer] = useState("");

  // Shared fields
  const [maxIncline, setMaxIncline] = useState(""); // %
  const [minPileReveal, setMinPileReveal] = useState(""); // m
  const [maxPileReveal, setMaxPileReveal] = useState(""); // m
  const [installationTolerance, setInstallationTolerance] = useState(""); // m
  const [trackerEdgeOverhang, setTrackerEdgeOverhang] = useState(""); // m

  // XTR-only
  const [max_segment_deflection_deg, set_max_segment_deflection_deg] = useState(""); // %
  const [max_cumulative_deflection_deg, set_max_cumulative_deflection_deg] = useState(""); // %

  // Module geometry
  const [moduleLength, setModuleLength] = useState(""); // m
  const [moduleWidth, setModuleWidth] = useState(""); // m
  const [minClearance, setMinClearance] = useState(""); // m
  const [maxTiltAngle, setMaxTiltAngle] = useState("60"); // deg ✅ NEW (default 60)

  // Shading analysis
  const [shadingEnabled, setShadingEnabled] = useState(false);
  const [azimuth, setAzimuth] = useState(""); // deg
  const [zenith, setZenith] = useState(""); // deg
  const [sunAngle, setSunAngle] = useState(""); // deg

  const [error, setError] = useState("");

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("pcl_parameters") || "null");
      if (saved) {
        setManufacturer(saved.manufacturer ?? "");
        setTrackerType(saved.trackerType ?? trackerTypeFromState);

        setMaxIncline(saved.maxIncline ?? "");
        setMinPileReveal(saved.minPileReveal ?? "");
        setMaxPileReveal(saved.maxPileReveal ?? "");
        setInstallationTolerance(saved.installationTolerance ?? "");
        setTrackerEdgeOverhang(saved.trackerEdgeOverhang ?? "");

        set_max_segment_deflection_deg(saved.max_segment_deflection_deg ?? "");
        set_max_cumulative_deflection_deg(saved.max_cumulative_deflection_deg ?? "");

        setModuleLength(saved.moduleLength ?? "");
        setModuleWidth(saved.moduleWidth ?? "");
        setMinClearance(saved.minClearance ?? "");
        setMaxTiltAngle(saved.maxTiltAngle ?? "60"); // ✅ restore

        setShadingEnabled(Boolean(saved.shadingEnabled));
        setAzimuth(saved.azimuth ?? "");
        setZenith(saved.zenith ?? "");
        setSunAngle(saved.sunAngle ?? "");
      }
    } catch {
      // ignore
    }

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

  const halfTolerance = useMemo(() => {
    const t = Number(installationTolerance);
    if (!Number.isFinite(t) || t <= 0) return null;
    return t / 2;
  }, [installationTolerance]);

  useEffect(() => {
    setError("");
    if (trackerType === "flat") {
      set_max_segment_deflection_deg("");
      set_max_cumulative_deflection_deg("");
    }
  }, [trackerType]);

  useEffect(() => {
    if (!shadingEnabled) {
      setAzimuth("");
      setZenith("");
      setSunAngle("");
    }
  }, [shadingEnabled]);

  function validateRequired() {
    if (
      !maxIncline ||
      !minPileReveal ||
      !maxPileReveal ||
      !installationTolerance ||
      !trackerEdgeOverhang
    ) {
      return "Please complete all required fields.";
    }

    if (trackerType === "xtr") {
      if (!max_segment_deflection_deg || !max_cumulative_deflection_deg) {
        return "Please complete all required XTR slope change fields.";
      }
    }

    if (!moduleLength || !moduleWidth || !minClearance || !maxTiltAngle) {
      return "Please enter Module length, Module width, Minimum clearance, and Max tilt angle.";
    }

    if (shadingEnabled) {
      if (!azimuth || !zenith || !sunAngle) {
        return "Please enter Azimuth, Zenith, and Sun Angle for shading analysis.";
      }
    }

    const minPR = Number(minPileReveal);
    const maxPR = Number(maxPileReveal);
    if (Number.isFinite(minPR) && Number.isFinite(maxPR) && maxPR < minPR) {
      return "Maximum pile reveal height must be greater than or equal to minimum pile reveal height.";
    }

    const mL = Number(moduleLength);
    const mW = Number(moduleWidth);
    const mC = Number(minClearance);
    const mT = Number(maxTiltAngle);

    if ((Number.isFinite(mL) && mL <= 0) || (Number.isFinite(mW) && mW <= 0)) {
      return "Module length and width must be positive numbers.";
    }
    if (!Number.isFinite(mC) || mC <= 0) {
      return "Minimum clearance must be a positive number.";
    }
    if (!Number.isFinite(mT) || mT <= 0 || mT >= 90) {
      return "Max tilt angle must be between 0 and 90 degrees (exclusive).";
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

      maxIncline,
      minPileReveal,
      maxPileReveal,
      installationTolerance,
      trackerEdgeOverhang,

      max_segment_deflection_deg: trackerType === "xtr" ? max_segment_deflection_deg : "",
      max_cumulative_deflection_deg: trackerType === "xtr" ? max_cumulative_deflection_deg : "",

      moduleLength,
      moduleWidth,
      minClearance,
      maxTiltAngle, // ✅ NEW

      shadingEnabled,
      azimuth: shadingEnabled ? azimuth : "",
      zenith: shadingEnabled ? zenith : "",
      sunAngle: shadingEnabled ? sunAngle : "",
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
      <div className="pr-bg" aria-hidden="true">
        <img src={backgroundImage} alt="" className="pr-bgImg" />
        <div className="pr-bgOverlay" />
        <div className="pr-gridOverlay" />
      </div>

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
                  ? "Maximum incline, Min/Max pile reveal, Tracker edge overhang, Maximum segment deflection (deg), Maximum cumulative deflection (deg), Installation tolerance"
                  : "Maximum incline, Min/Max pile reveal, Tracker edge overhang, Installation tolerance"}
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

              {trackerType === "xtr" && (
                <>
                  <div className="pr-field">
                    <label className="pr-label">Maximum segment deflection (deg)</label>
                    <input
                      className="pr-input"
                      type="number"
                      value={max_segment_deflection_deg}
                      onChange={(e) => set_max_segment_deflection_deg(e.target.value)}
                      placeholder="e.g., 0.5"
                    />
                  </div>

                  <div className="pr-field">
                    <label className="pr-label">Maximum cumulative deflection (deg)</label>
                    <input
                      className="pr-input"
                      type="number"
                      value={max_cumulative_deflection_deg}
                      onChange={(e) => set_max_cumulative_deflection_deg(e.target.value)}
                      placeholder="e.g., 4.0"
                    />
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

          {/* Module geometry */}
          <section className="pr-card">
            <div className="pr-cardHead">
              <div>
                <h2 className="pr-cardTitle">Module Geometry</h2>
                <p className="pr-cardSub">Used for clearance checks and (optionally) shading analysis.</p>
              </div>
            </div>

            <div className="pr-formGrid">
              <div className="pr-field">
                <label className="pr-label">Module length (m)</label>
                <input
                  className="pr-input"
                  type="number"
                  value={moduleLength}
                  onChange={(e) => setModuleLength(e.target.value)}
                  placeholder="e.g., 2.279"
                />
              </div>

              <div className="pr-field">
                <label className="pr-label">Module width (m)</label>
                <input
                  className="pr-input"
                  type="number"
                  value={moduleWidth}
                  onChange={(e) => setModuleWidth(e.target.value)}
                  placeholder="e.g., 1.134"
                />
              </div>

              <div className="pr-field">
                <label className="pr-label">Minimum required clearance (m)</label>
                <input
                  className="pr-input"
                  type="number"
                  value={minClearance}
                  onChange={(e) => setMinClearance(e.target.value)}
                  placeholder="e.g., 0.800"
                />
              </div>

              {/* ✅ NEW: max tilt angle */}
              <div className="pr-field">
                <label className="pr-label">Max tilt angle from horizontal (deg)</label>
                <input
                  className="pr-input"
                  type="number"
                  value={maxTiltAngle}
                  onChange={(e) => setMaxTiltAngle(e.target.value)}
                  placeholder="e.g., 60"
                />
                <div className="pr-hint">
                  Tilt of the module relative to the horizontal. Default is 60°. (Angle to pile becomes 90° − tilt.)
                </div>
              </div>
            </div>
          </section>

          {/* Shading analysis */}
          <section className="pr-card">
            <div className="pr-cardHead pr-cardHeadTight">
              <div>
                <h2 className="pr-cardTitle">Shading Analysis</h2>
                <p className="pr-cardSub">Enable this to enter sun position inputs (used in shading computations).</p>
              </div>

              <div className="pr-pill">
                <span className="pr-pillDot" />
                Optional
              </div>
            </div>

            <div className="pr-toggleRow">
              <button
                className={`pr-toggleBtn ${!shadingEnabled ? "is-active" : ""}`}
                onClick={() => setShadingEnabled(false)}
                type="button"
              >
                Off
              </button>

              <button
                className={`pr-toggleBtn ${shadingEnabled ? "is-active" : ""}`}
                onClick={() => setShadingEnabled(true)}
                type="button"
              >
                On
              </button>
            </div>

            {shadingEnabled && (
              <>
                <div className="pr-note">
                  Required when enabled: <strong>Azimuth, Zenith, Sun Angle</strong>
                </div>

                <div className="pr-formGrid">
                  <div className="pr-field">
                    <label className="pr-label">Azimuth (deg)</label>
                    <input className="pr-input" type="number" value={azimuth} onChange={(e) => setAzimuth(e.target.value)} />
                  </div>

                  <div className="pr-field">
                    <label className="pr-label">Zenith (deg)</label>
                    <input className="pr-input" type="number" value={zenith} onChange={(e) => setZenith(e.target.value)} />
                  </div>

                  <div className="pr-field">
                    <label className="pr-label">Sun angle (deg)</label>
                    <input className="pr-input" type="number" value={sunAngle} onChange={(e) => setSunAngle(e.target.value)} />
                  </div>
                </div>
              </>
            )}
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
