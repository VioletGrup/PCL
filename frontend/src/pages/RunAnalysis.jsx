import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import Plot from "react-plotly.js";
import "./RunAnalysis.css";

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
  const PAGE_SIZE = 100;

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
        !Array.isArray(frameLS) || !frameLS.length ||
        !Array.isArray(poleLS) || !poleLS.length ||
        !Array.isArray(xLS) || !xLS.length ||
        !Array.isArray(yLS) || !yLS.length
      ) {
        setError(
          "Missing Frame/Pole/X/Y data. Go back to Review and ensure Frame + Pole + X + Y columns are loaded."
        );
        return;
      }

      setFrame(frameLS);
      setPole(poleLS);
      setX(xLS);
      setY(yLS);

      // Restore grading results if coming back from FramePage
      if (state?.gradingResults) {
        setGradingResults(state.gradingResults);
      }
    } catch {
      setError("Failed to load data. Go back to Review and try again.");
    }
  }, [state]);

  // Build fast arrays for Plotly (one trace)
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

      cd.push({ frame: f, pole: p, label: `${f}.${p}` });
    }

    return {
      xNum: xx,
      yNum: yy,
      customData: cd,
      pointCount: xx.length,
      dropped: drop,
    };
  }, [frame, pole, x, y]);

  function goBack() {
    navigate("/parameters");
  }

  function onPlotClick(e) {
    const pt = e?.points?.[0];
    if (!pt) return;

    const cd = pt.customdata;
    const frameId = cd?.frame;

    if (!frameId || frameId === "—") return;

    let trackerResults = null;
    if (gradingResults && gradingResults.piles) {
      const tid = parseInt(frameId);
      const piles = gradingResults.piles.filter(p => Math.floor(p.pile_id) === tid);

      if (piles.length > 0) {
        const violations = gradingResults.violations.filter(v => Math.floor(v.pile_id) === tid);

        trackerResults = {
          tracker_id: tid,
          tracker_type: trackerType,
          piles: piles,
          violations: violations,
          total_cut: piles.reduce((sum, p) => sum + (p.cut_fill > 0 ? p.cut_fill : 0), 0),
          total_fill: piles.reduce((sum, p) => sum + (p.cut_fill < 0 ? Math.abs(p.cut_fill) : 0), 0),
          constraints: gradingResults.constraints // Pass constraints for side view
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
          const pileId = parseFloat(`${f}.${p.padStart(2, '0')}`);

          piles.push({
            pile_id: pileId,
            pile_in_tracker: parseInt(p),
            easting: xv,
            northing: yv,
            initial_elevation: zv,
            flooding_allowance: 0.0
          });
        }
      }

      if (piles.length === 0) {
        throw new Error("No valid piles found to grade.");
      }

      const params = JSON.parse(localStorage.getItem("pcl_parameters") || "{}");

      const request = {
        tracker_type: trackerType,
        piles: piles,
        constraints: {
          min_reveal_height: parseFloat(params.minPileReveal),
          max_reveal_height: parseFloat(params.maxPileReveal),
          pile_install_tolerance: parseFloat(params.installationTolerance),
          max_incline: parseFloat(params.maxIncline),
          target_height_percantage: 0.5,
          max_angle_rotation: 0.0,
          max_segment_deflection_deg: params.maxSegmentSlopeChange ? parseFloat(params.maxSegmentSlopeChange) : null,
          max_cumulative_deflection_deg: params.maxCumulativeSlopeChange ? parseFloat(params.maxCumulativeSlopeChange) : null,
        }
      };

      const res = await fetch("http://127.0.0.1:8000/api/grade-project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request)
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
      "tracker_id", "pile_id", "pile_in_tracker", "northing", "easting",
      "initial_elevation", "final_elevation", "change", "total_height", "total_revealed"
    ];

    const rows = gradingResults.piles.map(p => {
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
        p.pile_revealed
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

    // 1. Identify trackers with violations
    if (gradingResults.violations) {
      gradingResults.violations.forEach(v => {
        const tid = Math.floor(v.pile_id);
        statusMap.set(tid, "violation");
      });
    }

    // 2. Identify trackers that were graded
    gradingResults.piles.forEach(p => {
      const tid = Math.floor(p.pile_id);
      if (statusMap.get(tid) === "violation") return;

      if (Math.abs(p.cut_fill) > 0.0001) {
        statusMap.set(tid, "graded");
      } else if (!statusMap.has(tid)) {
        statusMap.set(tid, "ok");
      }
    });

    return statusMap;
  }, [gradingResults]);

  // Categorize and filter trackers for the sidebar
  const { filteredGraded, filteredAll, totalAllCount, pages } = useMemo(() => {
    if (!gradingResults) return { filteredGraded: [], filteredAll: [], totalAllCount: 0, pages: [] };

    const search = sidebarSearch.trim().toLowerCase();
    const uniqueTrackers = Array.from(new Set(gradingResults.piles.map(p => Math.floor(p.pile_id)))).sort((a, b) => a - b);

    // 1. Filter by search
    const matchedTrackers = uniqueTrackers.filter(tid => {
      return !search || tid.toString().includes(search);
    });

    // 2. Separate Graded/Violations
    const graded = matchedTrackers.filter(tid => {
      const status = trackerStatusMap.get(tid);
      return status === "graded" || status === "violation";
    });

    const total = matchedTrackers.length;
    let finalAll = matchedTrackers;
    let pageList = [];

    if (search) {
      // If searching, show all matches (up to a limit for performance)
      finalAll = matchedTrackers.slice(0, 200);
    } else {
      // If not searching, use range-based pagination for the "All" list
      const numPages = Math.ceil(total / PAGE_SIZE);
      for (let i = 0; i < numPages; i++) {
        const start = i * PAGE_SIZE + 1;
        const end = Math.min((i + 1) * PAGE_SIZE, total);
        pageList.push({ index: i, label: `${start}-${end}` });
      }

      const startIdx = okPage * PAGE_SIZE;
      finalAll = matchedTrackers.slice(startIdx, startIdx + PAGE_SIZE);
    }

    return {
      filteredGraded: graded,
      filteredAll: finalAll,
      totalAllCount: total,
      pages: pageList
    };
  }, [gradingResults, trackerStatusMap, sidebarSearch, okPage]);

  const handleTrackerClick = (tid) => {
    const piles = gradingResults.piles.filter(p => Math.floor(p.pile_id) === tid);
    if (piles.length === 0) return;

    const violations = gradingResults.violations.filter(v => Math.floor(v.pile_id) === tid);

    const trackerResults = {
      tracker_id: tid,
      tracker_type: trackerType,
      piles: piles,
      violations: violations,
      total_cut: piles.reduce((sum, p) => sum + (p.cut_fill > 0 ? p.cut_fill : 0), 0),
      total_fill: piles.reduce((sum, p) => sum + (p.cut_fill < 0 ? Math.abs(p.cut_fill) : 0), 0),
      constraints: gradingResults.constraints
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

  return (
    <div className="ra-shell">
      <header className="ra-topbar">
        <div className="ra-left">
          <Link to="/parameters" className="ra-link">
            ← Back
          </Link>

          <div className="ra-titlewrap">
            <h1 className="ra-title">Run Analysis</h1>
            <div className="ra-subtitle">
              Scatter plot (X vs Y). Hover shows <strong>Frame.Pole</strong>. Click a point to open that frame.
            </div>
          </div>
        </div>

        <div className="ra-meta">
          <div className="ra-chip">
            <div className="ra-chip-label">File</div>
            <div className="ra-chip-value">{fileName || "—"}</div>
          </div>
          <div className="ra-chip">
            <div className="ra-chip-label">Sheet</div>
            <div className="ra-chip-value">{sheetName || "—"}</div>
          </div>
          <div className="ra-chip">
            <div className="ra-chip-label">Tracker</div>
            <div className="ra-chip-value">{trackerType.toUpperCase()}</div>
          </div>
          <div className="ra-chip">
            <div className="ra-chip-label">Points</div>
            <div className="ra-chip-value">{pointCount.toLocaleString()}</div>
          </div>
        </div>
      </header>

      {error && <div className="ra-error">{error}</div>}

      {!error && (
        <div className={`ra-main-container ${sidebarOpen ? 'sidebar-open' : ''}`}>
          {gradingResults && (
            <button
              className="ra-sidebar-toggle"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              title={sidebarOpen ? "Close Sidebar" : "Open Tracker List"}
            >
              {sidebarOpen ? "«" : "»"}
            </button>
          )}

          {sidebarOpen && gradingResults && (
            <aside className="ra-sidebar">
              <div className="ra-sidebar-search-wrap">
                <input
                  type="text"
                  className="ra-sidebar-search"
                  placeholder="Search Tracker ID..."
                  value={sidebarSearch}
                  onChange={(e) => setSidebarSearch(e.target.value)}
                />
                {sidebarSearch && (
                  <button className="ra-search-clear" onClick={() => setSidebarSearch("")}>×</button>
                )}
              </div>

              <div className="ra-sidebar-section">
                <h3 className="ra-sidebar-title">Needs Grading / Violations ({filteredGraded.length})</h3>
                <div className="ra-sidebar-list">
                  {filteredGraded.map(tid => {
                    const status = trackerStatusMap.get(tid);
                    const statusClass = status === "violation" ? "violation" : "graded";
                    return (
                      <button
                        key={tid}
                        className={`ra-sidebar-item ${statusClass}`}
                        onClick={() => handleTrackerClick(tid)}
                      >
                        Tracker {tid}
                      </button>
                    );
                  })}
                  {filteredGraded.length === 0 && <div className="ra-no-results">No matches</div>}
                </div>
              </div>

              <div className="ra-sidebar-section">
                <h3 className="ra-sidebar-title">
                  All Trackers ({totalAllCount})
                </h3>

                {!sidebarSearch && pages.length > 1 && (
                  <div className="ra-sidebar-pagination">
                    <select
                      className="ra-sidebar-select"
                      value={okPage}
                      onChange={(e) => setOkPage(parseInt(e.target.value))}
                    >
                      {pages.map(p => (
                        <option key={p.index} value={p.index}>Range: {p.label}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="ra-sidebar-list">
                  {filteredAll.map(tid => {
                    const status = trackerStatusMap.get(tid);
                    const statusClass = status === "violation" ? "violation" : status === "graded" ? "graded" : "ok";
                    return (
                      <button
                        key={tid}
                        className={`ra-sidebar-item ${statusClass}`}
                        onClick={() => handleTrackerClick(tid)}
                      >
                        Tracker {tid}
                      </button>
                    );
                  })}
                  {filteredAll.length === 0 && <div className="ra-no-results">No matches</div>}
                </div>
                {!sidebarSearch && pages.length > 1 && (
                  <div className="ra-sidebar-tip">Select a range above to see more</div>
                )}
              </div>
            </aside>
          )}

          <div className="ra-plotwrap">
            <Plot
              data={[
                {
                  type: "scattergl",
                  mode: "markers",
                  x: xNum,
                  y: yNum,
                  customdata: customData,
                  marker: {
                    size: 4,
                    color: gradingResults ? xNum.map((_, i) => {
                      const cd = customData[i];
                      const tid = parseInt(cd.frame);
                      const status = trackerStatusMap.get(tid);

                      if (status === "violation") return "#FF4D4D"; // Red
                      if (status === "graded") return "#FF9800";    // Orange
                      return "#00C853";                             // Green
                    }) : "#FFD400",
                    opacity: 0.85,
                  },
                  hovertemplate: "%{customdata.label}<extra></extra>",
                  name: "Frame Locations",
                },
              ]}
              layout={{
                autosize: true,
                margin: { l: 60, r: 20, t: 30, b: 55 },
                paper_bgcolor: "#ffffff",
                plot_bgcolor: "#ffffff",
                xaxis: {
                  title: "X",
                  zeroline: false,
                  showgrid: true,
                  gridcolor: "#eef2f7",
                },
                yaxis: {
                  title: "Y",
                  zeroline: false,
                  showgrid: true,
                  gridcolor: "#eef2f7",
                },
                showlegend: false,
                hovermode: "closest",
                uirevision: "true", // ✅ Maintain zoom/pan after grading
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
        </div>
      )}

      {!error && (
        <footer className="ra-footer">
          Hover shows Frame.Pole. Dropped non-numeric rows:{" "}
          <strong>{dropped.toLocaleString()}</strong>.
        </footer>
      )}

      <div className="ra-actions">
        <button className="ra-btn" onClick={goBack}>
          ← Back to Parameters
        </button>
        <button
          className="ra-btn ra-btn-primary"
          onClick={runGrading}
          disabled={gradingLoading}
        >
          {gradingLoading ? "Running Grading..." : "Run Grading"}
        </button>
        {gradingResults && (
          <>
            <button className="ra-btn ra-btn-success" onClick={downloadCSV}>
              Download CSV
            </button>
            <button className="ra-btn" onClick={() => navigate("/uploads")}>
              Back to Upload
            </button>
          </>
        )}
      </div>


    </div>
  );
}
