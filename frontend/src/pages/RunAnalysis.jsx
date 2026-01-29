import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import Plot from "react-plotly.js";
import "./RunAnalysis.css";

import pclLogo from "../assets/logos/pcllogo.png";
import backgroundImage from "../assets/logos/Australia-Office-2025.png";
import config from "../config";

export default function RunAnalysis() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const [fileName, setFileName] = useState(state?.fileName || "");
  const [sheetName, setSheetName] = useState(state?.sheetName || "");
  const [trackerType, setTrackerType] = useState(state?.trackerType || "flat");

  // data (from localStorage)
  const [frame, setFrame] = useState([]);
  const [pole, setPole] = useState([]);
  const [x, setX] = useState([]);
  const [y, setY] = useState([]);

  const [error, setError] = useState("");

  const [gradingResults, setGradingResults] = useState(null);
  const [gradingLoading, setGradingLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarSearch, setSidebarSearch] = useState("");
  const [okPage, setOkPage] = useState(0);
  const [legendOpen, setLegendOpen] = useState(true);
  const PAGE_SIZE = 100;

  // pile jump input (bottom)
  const [pileJump, setPileJump] = useState("");

  // toggle to visually group poles by tracker/frame
  const [groupByTracker, setGroupByTracker] = useState(false);

  // Helpers
  const toNum = (v) => {
    if (typeof v === "number") return Number.isFinite(v) ? v : null;
    const s = String(v ?? "").trim();
    if (s === "") return null;
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  };

  const toIdPiece = (v) => {
    const s = String(v ?? "").trim();
    if (!s) return "";
    const n = Number(s);
    if (Number.isFinite(n)) return String(Math.trunc(n));
    return s;
  };

  const pctToDeg = (pct) => {
    const n = toNum(pct);
    if (n === null) return null;
    const radians = Math.atan(n / 100);
    return (radians * 180) / Math.PI;
  };

  /**
   * Safely parses a raw ID string (e.g. "12.03" or "12.3") into a float representation.
   *
   * @safety
   * This function enforces a 2-digit pole convention to prevent precision ambiguity.
   * - "12.03" -> 12.03 (Tracker 12, Pole 3)
   * - "12.3"  -> 12.03 (Tracker 12, Pole 3) -- NOT Pole 30!
   * - "12.30" -> 12.30 (Tracker 12, Pole 30)
   *
   * This ensures that "12.1" is correctly interpreted as Pole 1 (.01), matching the backend convention.
   */
  const normalizePileId = (raw) => {
    const s = String(raw ?? "").trim();
    if (!s) return null;

    if (!s.includes(".")) return null;

    const [a, b = ""] = s.split(".");
    if (!a) return null;

    const tracker = Number(a);
    if (!Number.isFinite(tracker)) return null;

    const poleRaw = b.replace(/[^\d]/g, "");
    if (!poleRaw) return null;

    const pole2 = poleRaw.padStart(2, "0").slice(-2);
    const id = `${Math.trunc(tracker)}.${pole2}`;
    const parsed = Number(id);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const findPileById = (piles, pileIdNum) => {
    const target = Math.round(pileIdNum * 100);
    return piles.find((p) => Math.round(Number(p.pile_id) * 100) === target) || null;
  };

  // Grouping style (outline + symbol) by FRAME
  const FRAME_OUTLINE_PALETTE = [
    "#0B5B3F",
    "#F2C300",
    "#2563EB",
    "#7C3AED",
    "#14B8A6",
    "#F97316",
    "#DB2777",
    "#06B6D4",
    "#22C55E",
    "#A3E635",
  ];

  const FRAME_SYMBOLS = ["circle", "square", "diamond", "triangle-up", "cross", "x"];

  const hashStr = (s) => {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return h;
  };

  const frameStyle = (frameStr) => {
    const s = String(frameStr ?? "");
    if (!s || s === "—") return { lineColor: "rgba(15,23,42,0.45)", symbol: "circle" };

    const n = Number(s);
    const key = Number.isFinite(n) ? Math.abs(Math.trunc(n)) : hashStr(s);

    return {
      lineColor: FRAME_OUTLINE_PALETTE[key % FRAME_OUTLINE_PALETTE.length],
      symbol: FRAME_SYMBOLS[key % FRAME_SYMBOLS.length],
    };
  };

  const markerSize = groupByTracker ? 6 : 4;
  const markerOutlineWidth = groupByTracker ? 1.8 : 0;

  useEffect(() => {
    setError("");

    try {
      const cfg = JSON.parse(localStorage.getItem("pcl_config") || "{}");
      setFileName(state?.fileName || cfg.fileName || "");
      setSheetName(state?.sheetName || cfg.sheetName || "");
      setTrackerType(state?.trackerType || cfg.trackerType || "flat");

      const frameLS = JSON.parse(localStorage.getItem("pcl_columns_frame") || "[]");
      const poleLS = JSON.parse(localStorage.getItem("pcl_columns_pole") || "[]");
      const xLS = JSON.parse(localStorage.getItem("pcl_columns_x") || "[]");
      const yLS = JSON.parse(localStorage.getItem("pcl_columns_y") || "[]");

      if (
        !Array.isArray(frameLS) ||
        !frameLS.length ||
        !Array.isArray(poleLS) ||
        !poleLS.length ||
        !Array.isArray(xLS) ||
        !xLS.length ||
        !Array.isArray(yLS) ||
        !yLS.length
      ) {
        setError("Missing Frame/Pole/X/Y data. Go back to Review and ensure Frame + Pole + X + Y columns are loaded.");
        return;
      }

      setFrame(frameLS);
      setPole(poleLS);
      setX(xLS);
      setY(yLS);

      if (state?.gradingResults) setGradingResults(state.gradingResults);
    } catch {
      setError("Failed to load data. Go back to Review and try again.");
    }
  }, [state]);

  // Build fast arrays for Plotly
  const { xNum, yNum, customData, pointCount, dropped } = useMemo(() => {
    const n = Math.min(frame.length, pole.length, x.length, y.length);

    const xx = [];
    const yy = [];
    const cd = [];
    let drop = 0;

    for (let i = 0; i < n; i++) {
      const xv = toNum(x[i]);
      const yv = toNum(y[i]);

      if (xv === null || yv === null) {
        drop++;
        continue;
      }

      const f = toIdPiece(frame[i]) || "—";
      const p = toIdPiece(pole[i]) || "—";

      xx.push(xv);
      yy.push(yv);
      cd.push({
        frame: f,
        pole: p,
        label: `${f}.${p}`,
        frameLabel: `${f}`, // ✅ used when grouped mode ON
      });
    }

    return {
      xNum: xx,
      yNum: yy,
      customData: cd,
      pointCount: xx.length,
      dropped: drop,
    };
  }, [frame, pole, x, y]);

  function onPlotClick(e) {
    const pt = e?.points?.[0];
    if (!pt) return;

    const cd = pt.customdata;
    const frameId = cd?.frame;

    if (!frameId || frameId === "—") return;

    let trackerResults = null;
    if (gradingResults && gradingResults.piles) {
      const tid = parseInt(frameId);
      const piles = gradingResults.piles.filter((p) => Math.floor(p.pile_id) === tid);

      if (piles.length > 0) {
        const violations = (gradingResults.violations || []).filter((v) => Math.floor(v.pile_id) === tid);

        const metrics = gradingResults.tracker_metrics?.[tid];

        trackerResults = {
          tracker_id: tid,
          tracker_type: trackerType,
          piles: piles,
          violations: violations,
          total_cut: piles.reduce((sum, p) => sum + (p.cut_fill > 0 ? p.cut_fill : 0), 0),
          total_fill: piles.reduce((sum, p) => sum + (p.cut_fill < 0 ? Math.abs(p.cut_fill) : 0), 0),
          constraints: gradingResults.constraints,
          // ✅ Pass XTR metrics
          north_wing_deflection: metrics?.north_wing_deflection,
          south_wing_deflection: metrics?.south_wing_deflection,
          max_tracker_degree_break: metrics?.max_tracker_degree_break,
        };
      }
    }

    if (!trackerResults) {
      alert("Please run grading first to view the side profile.");
      return;
    }

    navigate(`/frame/${encodeURIComponent(frameId)}`, {
      state: {
        frameId,
        fileName,
        sheetName,
        trackerType,
        trackerResults,
        gradingResults,
      },
    });
  }

  async function runGrading() {
    setGradingLoading(true);
    setError("");
    setGradingResults(null);

    try {
      const piles = [];
      const zLS = JSON.parse(localStorage.getItem("pcl_columns_z") || "[]");
      const n = Math.min(frame.length, pole.length, x.length, y.length, zLS.length);

      for (let i = 0; i < n; i++) {
        const f = toIdPiece(frame[i]);
        const p = toIdPiece(pole[i]);
        const xv = toNum(x[i]);
        const yv = toNum(y[i]);
        const zv = toNum(zLS[i]);
        if (f && p && xv !== null && yv !== null && zv !== null) {
          const pileId = parseFloat(`${f}.${p.padStart(2, "0")}`);

          piles.push({
            pile_id: pileId,
            pile_in_tracker: parseInt(p),
            easting: xv,
            northing: yv,
            initial_elevation: zv,
            flooding_allowance: 0.0,
          });
        }
      }

      if (piles.length === 0) throw new Error("No valid piles found to grade.");

      const params = JSON.parse(localStorage.getItem("pcl_parameters") || "{}");

      // ✅ XTR: Pass degrees directly (no pctToDeg)
      const segDefDeg =
        trackerType === "xtr" && params.max_segment_deflection_deg ? parseFloat(params.max_segment_deflection_deg) : null;

      const cumDefDeg =
        trackerType === "xtr" && params.max_cumulative_deflection_deg ? parseFloat(params.max_cumulative_deflection_deg) : null;

      const request = {
        tracker_type: trackerType,
        piles: piles,
        constraints: {
          min_reveal_height: parseFloat(params.minPileReveal),
          max_reveal_height: parseFloat(params.maxPileReveal),
          pile_install_tolerance: parseFloat(params.installationTolerance),
          max_incline: parseFloat(params.maxIncline),
          target_height_percentage: 0.5,
          max_angle_rotation: 0.0,
          tracker_edge_overhang: params.trackerEdgeOverhang ? parseFloat(params.trackerEdgeOverhang) : 0.0,
          max_segment_deflection_deg: segDefDeg,
          max_cumulative_deflection_deg: cumDefDeg,
        },
      };

      const res = await fetch(`${config.API_BASE_URL}/api/grade-project`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText);
      }

      const result = await res.json();
      setGradingResults(result);
    } catch (e) {
      setError(e.message || "Grading failed");
    } finally {
      setGradingLoading(false);
    }
  }

  function downloadCSV() {
    if (!gradingResults || !gradingResults.piles) return;

    const headers = [
      "tracker_id",
      "pile_id",
      "pile_in_tracker",
      "northing",
      "easting",
      "initial_elevation",
      "final_elevation",
      "change",
      "total_height",
      "total_revealed",
    ];

    const rows = gradingResults.piles.map((p) => {
      const trackerId = Math.floor(p.pile_id);
      const change = p.final_elevation - p.initial_elevation;
      return [
        trackerId,
        p.pile_id,
        p.pile_in_tracker,
        p.northing,
        p.easting,
        p.initial_elevation,
        p.final_elevation,
        change,
        p.total_height,
        p.pile_revealed,
      ].join(",");
    });

    const csvContent = [headers.join(","), ...rows].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `grading_results_${new Date().getTime()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Pre-calculate tracker statuses for fast coloring
  const trackerStatusMap = useMemo(() => {
    if (!gradingResults || !gradingResults.piles) return new Map();

    const statusMap = new Map();

    if (gradingResults.violations) {
      gradingResults.violations.forEach((v) => {
        const tid = Math.floor(v.pile_id);
        statusMap.set(tid, "violation");
      });
    }

    gradingResults.piles.forEach((p) => {
      const tid = Math.floor(p.pile_id);
      if (statusMap.get(tid) === "violation") return;

      if (Math.abs(p.cut_fill) > 0.0001) statusMap.set(tid, "graded");
      else if (!statusMap.has(tid)) statusMap.set(tid, "ok");
    });

    return statusMap;
  }, [gradingResults]);

  const { filteredGraded, filteredAll, totalAllCount, pages } = useMemo(() => {
    if (!gradingResults) return { filteredGraded: [], filteredAll: [], totalAllCount: 0, pages: [] };

    const search = sidebarSearch.trim().toLowerCase();
    const uniqueTrackers = Array.from(new Set(gradingResults.piles.map((p) => Math.floor(p.pile_id)))).sort(
      (a, b) => a - b
    );

    const matchedTrackers = uniqueTrackers.filter((tid) => !search || tid.toString().includes(search));

    const graded = matchedTrackers.filter((tid) => {
      const status = trackerStatusMap.get(tid);
      return status === "graded" || status === "violation";
    });

    const total = matchedTrackers.length;
    let finalAll = matchedTrackers;
    let pageList = [];

    if (search) {
      finalAll = matchedTrackers.slice(0, 200);
    } else {
      const numPages = Math.ceil(total / PAGE_SIZE);
      for (let i = 0; i < numPages; i++) {
        const start = i * PAGE_SIZE + 1;
        const end = Math.min((i + 1) * PAGE_SIZE, total);
        pageList.push({ index: i, label: `${start}-${end}` });
      }

      const startIdx = okPage * PAGE_SIZE;
      finalAll = matchedTrackers.slice(startIdx, startIdx + PAGE_SIZE);
    }

    return { filteredGraded: graded, filteredAll: finalAll, totalAllCount: total, pages: pageList };
  }, [gradingResults, trackerStatusMap, sidebarSearch, okPage]);

  const handleTrackerClick = (tid) => {
    const piles = gradingResults.piles.filter((p) => Math.floor(p.pile_id) === tid);
    if (piles.length === 0) return;

    const violations = (gradingResults.violations || []).filter((v) => Math.floor(v.pile_id) === tid);

    const metrics = gradingResults.tracker_metrics?.[tid];

    const trackerResults = {
      tracker_id: tid,
      tracker_type: trackerType,
      piles: piles,
      violations: violations,
      total_cut: piles.reduce((sum, p) => sum + (p.cut_fill > 0 ? p.cut_fill : 0), 0),
      total_fill: piles.reduce((sum, p) => sum + (p.cut_fill < 0 ? Math.abs(p.cut_fill) : 0), 0),
      constraints: gradingResults.constraints,
      // ✅ Pass XTR metrics
      north_wing_deflection: metrics?.north_wing_deflection,
      south_wing_deflection: metrics?.south_wing_deflection,
      max_tracker_degree_break: metrics?.max_tracker_degree_break,
    };

    navigate(`/frame/${encodeURIComponent(tid)}`, {
      state: {
        frameId: tid.toString(),
        fileName,
        sheetName,
        trackerType,
        trackerResults,
        gradingResults,
      },
    });
  };

  const goToPile = () => {
    if (!gradingResults || !gradingResults.piles) {
      alert("Run grading first, then you can jump to a pile.");
      return;
    }

    const pileIdNum = normalizePileId(pileJump);
    if (pileIdNum === null) {
      alert('Enter a Pile ID like "12.03" (tracker.pole). Example: 105.07');
      return;
    }

    const pileObj = findPileById(gradingResults.piles, pileIdNum);
    if (!pileObj) {
      alert(`Pile ${pileIdNum.toFixed(2)} not found in grading results.`);
      return;
    }

    const violation = (gradingResults.violations || []).find(
      (v) => Math.round(Number(v.pile_id) * 100) === Math.round(pileIdNum * 100)
    );

    navigate(`/pile/${encodeURIComponent(pileIdNum.toFixed(2))}`, {
      state: {
        pileId: pileIdNum.toFixed(2),
        pile: pileObj,
        violation: violation || null,
        fileName,
        sheetName,
        trackerType,
        gradingResults,
      },
    });
  };

  return (
    <div className="ra-shell">
      <div className="ra-bg" aria-hidden="true">
        <img src={backgroundImage} alt="" className="ra-bgImg" />
        <div className="ra-bgOverlay" />
        <div className="ra-gridOverlay" />
      </div>

      <header className="ra-header">
        <div className="ra-headerInner">
          <div className="ra-brand">
            <img src={pclLogo} alt="PCL Logo" className="ra-logo" />
            <div className="ra-brandText">
              <div className="ra-brandTitle">Earthworks Analysis Tool</div>
              <div className="ra-brandSub">Run → Visualise → Frame profile</div>
            </div>
          </div>

          <div className="ra-headerActions">
            <Link to="/parameters" className="ra-navLink">
              ← Back
            </Link>

            <button
              className={`ra-btn ${groupByTracker ? "ra-btnSuccess" : ""}`}
              onClick={() => setGroupByTracker((v) => !v)}
              title="When ON: same Frame shares the same marker outline + symbol"
            >
              {groupByTracker ? "Show Piles" : "Group by Tracker"}
            </button>

            <button
              className="ra-btn ra-btnPrimary"
              onClick={runGrading}
              disabled={gradingLoading}
              title="Run grading using backend constraints"
            >
              {gradingLoading ? "Running Grading..." : "Run Grading"}
            </button>

            {gradingResults && (
              <button className="ra-btn ra-btnSuccess" onClick={downloadCSV}>
                Download CSV
              </button>
            )}
          </div>
        </div>
      </header>

      <div className="ra-main">
        <div className="ra-metaRow">
          <div className="ra-chip">
            <div className="ra-chipLabel">File</div>
            <div className="ra-chipValue">{fileName || "—"}</div>
          </div>
          <div className="ra-chip">
            <div className="ra-chipLabel">Sheet</div>
            <div className="ra-chipValue">{sheetName || "—"}</div>
          </div>
          <div className="ra-chip">
            <div className="ra-chipLabel">Tracker</div>
            <div className="ra-chipValue">{trackerType.toUpperCase()}</div>
          </div>
          <div className="ra-chip">
            <div className="ra-chipLabel">Points</div>
            <div className="ra-chipValue">{pointCount.toLocaleString()}</div>
          </div>

        </div>

        {error && <div className="ra-alert ra-alertError">{error}</div>}

        {!error && (
          <div className={`ra-workspace ${sidebarOpen ? "sidebar-open" : ""}`}>
            {gradingResults && (
              <button
                className="ra-sidebarToggle"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                title={sidebarOpen ? "Close Tracker List" : "Open Tracker List"}
              >
                {sidebarOpen ? "«" : "»"}
              </button>
            )}

            {sidebarOpen && gradingResults && (
              <aside className="ra-sidebar">
                <div className="ra-sidebarHead">
                  <div className="ra-sidebarTitle">Trackers</div>
                  <div className="ra-sidebarSub">Search or pick a tracker to open its frame profile.</div>
                </div>

                <div className="ra-sidebarSearchWrap">
                  <input
                    type="text"
                    className="ra-sidebarSearch"
                    placeholder="Search Tracker ID..."
                    value={sidebarSearch}
                    onChange={(e) => setSidebarSearch(e.target.value)}
                  />
                  {sidebarSearch && (
                    <button className="ra-searchClear" onClick={() => setSidebarSearch("")} title="Clear">
                      ×
                    </button>
                  )}
                </div>

                <div className="ra-sidebarSection">
                  <div className="ra-sectionHead">
                    <div className="ra-sectionTitle">Needs Grading / Violations</div>
                    <div className="ra-sectionCount">{filteredGraded.length}</div>
                  </div>

                  <div className="ra-sidebarList">
                    {filteredGraded.map((tid) => {
                      const status = trackerStatusMap.get(tid);
                      const statusClass = status === "violation" ? "violation" : "graded";
                      return (
                        <button
                          key={tid}
                          className={`ra-sidebarItem ${statusClass}`}
                          onClick={() => handleTrackerClick(tid)}
                        >
                          <span className="ra-itemDot" />
                          Tracker {tid}
                        </button>
                      );
                    })}
                    {filteredGraded.length === 0 && <div className="ra-noResults">No matches</div>}
                  </div>
                </div>

                <div className="ra-sidebarSection">
                  <div className="ra-sectionHead">
                    <div className="ra-sectionTitle">All Trackers</div>
                    <div className="ra-sectionCount">{totalAllCount}</div>
                  </div>

                  {!sidebarSearch && pages.length > 1 && (
                    <div className="ra-sidebarPagination">
                      <select
                        className="ra-sidebarSelect"
                        value={okPage}
                        onChange={(e) => setOkPage(parseInt(e.target.value))}
                      >
                        {pages.map((p) => (
                          <option key={p.index} value={p.index}>
                            Range: {p.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="ra-sidebarList">
                    {filteredAll.map((tid) => {
                      const status = trackerStatusMap.get(tid);
                      const statusClass =
                        status === "violation" ? "violation" : status === "graded" ? "graded" : "ok";
                      return (
                        <button
                          key={tid}
                          className={`ra-sidebarItem ${statusClass}`}
                          onClick={() => handleTrackerClick(tid)}
                        >
                          <span className="ra-itemDot" />
                          Tracker {tid}
                        </button>
                      );
                    })}
                    {filteredAll.length === 0 && <div className="ra-noResults">No matches</div>}
                  </div>

                  {!sidebarSearch && pages.length > 1 && <div className="ra-sidebarTip">Select a range above to see more</div>}
                </div>
              </aside>
            )}

            <section className="ra-plotCard">
              <div className="ra-plotHead">
                <div>
                  <div className="ra-plotTitle">Site Layout (Easting (X) vs Northing (Y))</div>
                  <div className="ra-plotSub">
                    {groupByTracker ? (
                      <>
                        Hover shows <strong>Frame</strong> only. Click any point to open that frame.
                      </>
                    ) : (
                      <>
                        Hover shows <strong>Frame.Pole</strong>. Click a point to open that frame.
                      </>
                    )}
                  </div>

                  {/* ✅ Show XTR Metrics if present */}
                  {gradingResults?.tracker_metrics && (
                    <div className="ra-xtr-metrics" style={{ marginTop: 8, fontSize: "0.85rem", color: "#64748b" }}>
                      Project Metrics Available: Wing Deflection & Degree Break (View in Tracker Details)
                    </div>
                  )}
                </div>

                {gradingResults && (
                  <div className="ra-plotBadges">
                    <span className="ra-miniBadge danger">Violation</span>
                    <span className="ra-miniBadge warn">Graded</span>
                    <span className="ra-miniBadge ok">OK</span>
                  </div>
                )}
              </div>

              <div className="ra-plotWrap">
                <Plot
                  data={[
                    {
                      type: "scattergl",
                      mode: "markers",
                      x: xNum,
                      y: yNum,
                      customdata: customData,
                      marker: {
                        size: markerSize,
                        color: gradingResults
                          ? xNum.map((_, i) => {
                            const cd = customData[i];
                            const tid = parseInt(cd.frame);
                            const status = trackerStatusMap.get(tid);
                            if (status === "violation") return "#FF4D4D";
                            if (status === "graded") return "#FF9800";
                            return "#00C853";
                          })
                          : "#FFD400",

                        line: groupByTracker
                          ? {
                            width: markerOutlineWidth,
                            color: xNum.map((_, i) => frameStyle(customData[i]?.frame).lineColor),
                          }
                          : { width: 0, color: "rgba(0,0,0,0)" },

                        symbol: groupByTracker
                          ? xNum.map((_, i) => frameStyle(customData[i]?.frame).symbol)
                          : "circle",

                        opacity: 0.9,
                      },

                      // ✅ KEY CHANGE: hover shows Frame only when grouped mode is ON
                      hovertemplate: groupByTracker ? "Frame %{customdata.frame}<extra></extra>" : "%{customdata.label}<extra></extra>",
                      name: "Frame Locations",
                    },
                  ]}
                  layout={{
                    autosize: true,
                    margin: { l: 66, r: 24, t: 30, b: 58 },
                    paper_bgcolor: "rgba(0,0,0,0)",
                    plot_bgcolor: "rgba(0,0,0,0)",
                    xaxis: {
                      title: "X",
                      zeroline: false,
                      showgrid: true,
                      gridcolor: "rgb(18, 17, 17)",
                      tickformat: ",.0f",
                      separatethousands: true,
                    },
                    yaxis: {
                      title: "Y",
                      zeroline: false,
                      showgrid: true,
                      gridcolor: "rgb(0, 0, 0)",
                      tickformat: ",.0f",
                      separatethousands: true,
                    },
                    showlegend: false,
                    hovermode: "closest",
                    uirevision: "true",
                  }}
                  config={{
                    responsive: true,
                    displaylogo: false,
                    scrollZoom: true,
                    modeBarButtonsToRemove: ["lasso2d"],
                  }}
                  style={{ width: "100%", height: "100%" }}
                  onClick={onPlotClick}
                />
              </div>
            </section>

            {gradingResults && (
              <div className={`ra-legend ${legendOpen ? "open" : "closed"}`}>
                <button className="ra-legendToggle" onClick={() => setLegendOpen(!legendOpen)}>
                  {legendOpen ? "Hide Legend" : "Show Legend"}
                </button>

                {legendOpen && (
                  <div className="ra-legendContent">
                    <div className="ra-legendItem">
                      <span className="ra-legendDot red" />
                      <div className="ra-legendText">
                        <div className="ra-legendLabel">Violation</div>
                        <div className="ra-legendDesc">Still fails constraints after grading</div>
                      </div>
                    </div>

                    <div className="ra-legendItem">
                      <span className="ra-legendDot orange" />
                      <div className="ra-legendText">
                        <div className="ra-legendLabel">Graded</div>
                        <div className="ra-legendDesc">Fixed via ground adjustment (Cut/Fill)</div>
                      </div>
                    </div>

                    <div className="ra-legendItem">
                      <span className="ra-legendDot green" />
                      <div className="ra-legendText">
                        <div className="ra-legendLabel">OK</div>
                        <div className="ra-legendDesc">Valid without ground adjustment</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {!error && (
        <footer className="ra-footer">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div>
              Hover shows {groupByTracker ? "Frame" : "Frame.Pole"}. Dropped non-numeric rows:{" "}
              <strong>{dropped.toLocaleString()}</strong>.
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <input
                type="text"
                value={pileJump}
                onChange={(e) => setPileJump(e.target.value)}
                placeholder='Go to pile (e.g. 12.03)'
                style={{
                  height: 38,
                  padding: "0 12px",
                  borderRadius: 10,
                  border: "1px solid rgba(255,255,255,0.20)",
                  background: "rgba(255,255,255,0.10)",
                  color: "rgba(255,255,255,0.92)",
                  outline: "none",
                  minWidth: 210,
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") goToPile();
                }}
              />

              <button
                onClick={goToPile}
                style={{
                  height: 38,
                  padding: "0 14px",
                  borderRadius: 10,
                  border: "1px solid rgba(255,255,255,0.20)",
                  background: "rgba(242, 195, 0, 0.90)",
                  color: "#0b5b3f",
                  fontWeight: 900,
                  cursor: "pointer",
                }}
              >
                Open Pile
              </button>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}
