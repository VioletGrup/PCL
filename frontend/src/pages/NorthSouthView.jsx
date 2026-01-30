import { useMemo, useState } from "react";
import { Link, useLocation, useParams, useNavigate } from "react-router-dom";
import Plot from "react-plotly.js";
import "./NorthSouthView.css";

import pclLogo from "../assets/logos/pcllogo.png";
import backgroundImage from "../assets/logos/Australia-Office-2025.png";

export default function NorthSouthView() {
  /**
   * Purpose: North–South View (Front Elevation) — piles + module segments.
   * Name: NorthSouthView.jsx
   * Date created: 2026-01-29
   * Method:
   *  - X axis: Easting (m)
   *  - Y axis: Elevation (m)
   *  - Pile post: from final_elevation (base) to total_height (top elevation)
   *  - Module segment at pile top: width = MODULE WIDTH (m), scaled by depth (northing)
   *  - Base tick + base marker + base label (pile number)
   * Hover info: pile number, base elevation, top elevation.
   */

  const { frameId } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();

  const grading = state?.trackerResults || null;

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [pileJump, setPileJump] = useState("");

  const meta = useMemo(() => {
    return {
      fileName: state?.fileName || "",
      sheetName: state?.sheetName || "",
      trackerType: state?.trackerType || "flat",
    };
  }, [state]);

  // ✅ Module WIDTH from state OR localStorage (saved on Parameters page)
  const moduleWidth = useMemo(() => {
    const fromState = Number(state?.moduleWidth);
    if (Number.isFinite(fromState) && fromState > 0) return fromState;

    try {
      const saved = JSON.parse(localStorage.getItem("pcl_parameters") || "null");
      const fromLS = Number(saved?.moduleWidth);
      if (Number.isFinite(fromLS) && fromLS > 0) return fromLS;
    } catch {
      // ignore
    }
    return 0;
  }, [state]);

  const handlePileJump = (e) => {
    e.preventDefault();
    if (!grading?.piles?.length) return;

    const raw = String(pileJump || "").trim().replace(/^p/i, "");
    if (!raw) return;

    const pileInTrackerNum = Number(raw);
    if (!Number.isFinite(pileInTrackerNum) || !Number.isInteger(pileInTrackerNum) || pileInTrackerNum <= 0) return;

    const pileObj = grading.piles.find((p) => Number(p.pile_in_tracker) === pileInTrackerNum) || null;
    if (!pileObj) return;

    const violationObj =
      grading?.violations?.find((v) => Number(v.pile_id) === Number(pileObj.pile_id)) || null;

    navigate(`/pile/${encodeURIComponent(String(pileObj.pile_id))}`, {
      state: {
        ...state,
        pile: pileObj,
        violation: violationObj,
      },
    });
  };

  const plotTraces = useMemo(() => {
    if (!grading?.piles?.length) return [];

    // Sort by northing so depth scaling is consistent
    const piles = [...grading.piles].sort((a, b) => Number(a.northing) - Number(b.northing));

    const northings = piles.map((p) => Number(p.northing));
    const minN = Math.min(...northings);
    const maxN = Math.max(...northings);
    const nRange = maxN - minN || 1;

    const easting = piles.map((p) => Number(p.easting));
    const base = piles.map((p) => Number(p.final_elevation));
    // IMPORTANT: your model uses total_height as TOP ELEVATION
    const top = piles.map((p) => Number(p.total_height));

    // Category colours (same meaning as FramePage)
    const colors = piles.map((p) => {
      const isViolation = grading.violations?.some((v) => Number(v.pile_id) === Number(p.pile_id));
      const isGraded = Math.abs(Number(p.cut_fill)) > 0.0001;
      if (isViolation) return "#FF4D4D";
      if (isGraded) return "#FF9800";
      return "#424242";
    });

    // Dummy legend keys
    const legendKeys = [
      {
        x: [null],
        y: [null],
        type: "scatter",
        mode: "lines",
        name: "Pile: Violation",
        line: { color: "#FF4D4D", width: 4 },
        showlegend: true,
        hoverinfo: "skip",
      },
      {
        x: [null],
        y: [null],
        type: "scatter",
        mode: "lines",
        name: "Pile: Graded",
        line: { color: "#FF9800", width: 4 },
        showlegend: true,
        hoverinfo: "skip",
      },
      {
        x: [null],
        y: [null],
        type: "scatter",
        mode: "lines",
        name: "Pile: OK",
        line: { color: "#424242", width: 4 },
        showlegend: true,
        hoverinfo: "skip",
      },
      {
        x: [null],
        y: [null],
        type: "scatter",
        mode: "lines",
        name: "Module width (at top)",
        line: { color: "#1a237e", width: 6 },
        showlegend: true,
        hoverinfo: "skip",
      },
      {
        x: [null],
        y: [null],
        type: "scatter",
        mode: "markers",
        name: "Pile base marker",
        marker: { size: 8, color: "rgba(15,23,42,0.92)" },
        showlegend: true,
        hoverinfo: "skip",
      },
    ];

    // Base tick length (in x units), scaled from typical pile spacing
    const spacings = [];
    for (let i = 1; i < easting.length; i++) {
      const dx = Math.abs(easting[i] - easting[i - 1]);
      if (Number.isFinite(dx) && dx > 0) spacings.push(dx);
    }
    spacings.sort((a, b) => a - b);
    const medianDx = spacings.length ? spacings[Math.floor(spacings.length / 2)] : 1;
    const baseTickHalf = Math.max(0.05, Math.min(0.35, 0.18 * medianDx)); // half-length

    const pilePosts = [];
    const moduleSegments = [];
    const topMarkers = [];
    const baseMarkers = [];
    const baseTicks = [];
    const baseLabels = [];

    for (let i = 0; i < piles.length; i++) {
      const x = easting[i];
      const y0 = base[i];
      const y1 = top[i];

      if (!Number.isFinite(x) || !Number.isFinite(y0) || !Number.isFinite(y1)) continue;

      // Depth scaling (front = 1.0, far back = 0.4)
      const depthFactor = 1 - ((Number(piles[i].northing) - minN) / nRange) * 0.6;
      const widthFactor = Math.max(0.4, Math.min(1.0, depthFactor));

      const pileNo = Number(piles[i].pile_in_tracker);
      const hover =
        `Pile ${Number.isFinite(pileNo) ? pileNo : "—"}` +
        `<br>Base: ${y0.toFixed(3)} m` +
        `<br>Top: ${y1.toFixed(3)} m` +
        `<extra></extra>`;

      // Vertical pile
      pilePosts.push({
        x: [x, x],
        y: [y0, y1],
        type: "scatter",
        mode: "lines",
        showlegend: false,
        line: { color: colors[i], width: Math.max(2, 4 * widthFactor) },
        hovertemplate: hover,
      });

      // Top marker
      topMarkers.push({
        x: [x],
        y: [y1],
        type: "scatter",
        mode: "markers",
        showlegend: false,
        marker: {
          size: Math.max(6, 9 * widthFactor),
          color: colors[i],
          line: { width: 1, color: "rgba(255,255,255,0.85)" },
        },
        hovertemplate: hover,
      });

      // Base marker
      baseMarkers.push({
        x: [x],
        y: [y0],
        type: "scatter",
        mode: "markers",
        showlegend: false,
        marker: {
          size: Math.max(6, 9 * widthFactor),
          color: "rgba(15,23,42,0.92)",
          line: { width: 1, color: "rgba(255,255,255,0.75)" },
        },
        hovertemplate: hover,
      });

      // Base horizontal tick
      baseTicks.push({
        x: [x - baseTickHalf * widthFactor, x + baseTickHalf * widthFactor],
        y: [y0, y0],
        type: "scatter",
        mode: "lines",
        showlegend: false,
        line: { color: "rgba(15,23,42,0.75)", width: Math.max(1.5, 3 * widthFactor) },
        hoverinfo: "skip",
      });

      // Base label (pile number)
      if (Number.isFinite(pileNo)) {
        baseLabels.push({
          x: [x],
          y: [y0],
          type: "scatter",
          mode: "text",
          showlegend: false,
          text: [`${pileNo}`],
          textposition: "bottom center",
          textfont: { size: 11, color: "rgba(15,23,42,0.92)" },
          hoverinfo: "skip",
        });
      }

      // ✅ Module segment at top uses MODULE WIDTH
      if (Number.isFinite(moduleWidth) && moduleWidth > 0) {
        const segHalf = (moduleWidth / 2) * widthFactor;
        moduleSegments.push({
          x: [x - segHalf, x + segHalf],
          y: [y1, y1],
          type: "scatter",
          mode: "lines",
          showlegend: false,
          line: { color: "#1a237e", width: Math.max(2, 6 * widthFactor) },
          hoverinfo: "skip",
        });
      }
    }

    return [
      ...legendKeys,
      ...pilePosts,
      ...moduleSegments,
      ...topMarkers,
      ...baseTicks,
      ...baseMarkers,
      ...baseLabels,
    ];
  }, [grading, moduleWidth]);

  if (!grading) {
    return (
      <div className="nsv-shell">
        <div className="nsv-bg" aria-hidden="true">
          <img src={backgroundImage} alt="" className="nsv-bgImg" />
          <div className="nsv-bgOverlay" />
          <div className="nsv-gridOverlay" />
        </div>

        <div className="nsv-empty">
          <div className="nsv-emptyCard">
            <div className="nsv-emptyTitle">No grading results found</div>
            <div className="nsv-emptySub">
              Please go back to <strong>Run Analysis</strong> and click <strong>Run Grading</strong>.
            </div>
            <button className="nsv-btn nsv-btnPrimary" onClick={() => navigate("/run-analysis")}>
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="nsv-shell">
      {/* Background */}
      <div className="nsv-bg" aria-hidden="true">
        <img src={backgroundImage} alt="" className="nsv-bgImg" />
        <div className="nsv-bgOverlay" />
        <div className="nsv-gridOverlay" />
      </div>

      {/* Header */}
      <header className="nsv-header">
        <div className="nsv-headerInner">
          <div className="nsv-brand">
            <img src={pclLogo} alt="PCL Logo" className="nsv-logo" />
            <div className="nsv-brandText">
              <div className="nsv-brandTitle">Earthworks Analysis Tool</div>
              <div className="nsv-brandSub">North–South View • front elevation • piles + modules</div>
            </div>
          </div>

          <div className="nsv-headerActions">
            <Link to="/run-analysis" state={state} className="nsv-navLink">
              ← Back to Plot
            </Link>

            <Link
              to={`/frame/${encodeURIComponent(String(frameId))}`}
              state={state}
              className="nsv-navLink nsv-navLinkAlt"
              title="Return to East–West view"
            >
              ↔ East–West View
            </Link>

            <div className="nsv-stepPill" title="You are viewing the North–South profile">
              <span className="nsv-stepDot" />
              North–South View
            </div>
          </div>
        </div>
      </header>

      <div className="nsv-main">
        <div className="nsv-hero">
          <div className="nsv-badge">
            <span className="nsv-badgeDot" />
            Tracker Profile
          </div>
          <h1 className="nsv-h1">Tracker {frameId}</h1>
          <p className="nsv-subtitle">
            Hover shows: <strong>pile #</strong>, <strong>base</strong>, <strong>top</strong>.
            {moduleWidth > 0 ? ` Module width: ${moduleWidth} m.` : ""}
          </p>
        </div>

        <div className="nsv-metaRow">
          <div className="nsv-chip">
            <div className="nsv-chipLabel">File</div>
            <div className="nsv-chipValue">{meta.fileName || "—"}</div>
          </div>
          <div className="nsv-chip">
            <div className="nsv-chipLabel">Sheet</div>
            <div className="nsv-chipValue">{meta.sheetName || "—"}</div>
          </div>
          <div className="nsv-chip">
            <div className="nsv-chipLabel">Tracker</div>
            <div className="nsv-chipValue">{meta.trackerType.toUpperCase()}</div>
          </div>
          <div className="nsv-chip">
            <div className="nsv-chipLabel">Module W</div>
            <div className="nsv-chipValue">{moduleWidth > 0 ? `${moduleWidth} m` : "—"}</div>
          </div>
          <div className="nsv-chip">
            <div className="nsv-chipLabel">Total Cut</div>
            <div className="nsv-chipValue">{grading.total_cut.toFixed(2)} m</div>
          </div>
          <div className="nsv-chip">
            <div className="nsv-chipLabel">Total Fill</div>
            <div className="nsv-chipValue">{grading.total_fill.toFixed(2)} m</div>
          </div>
        </div>

        <div className={`nsv-workspace ${sidebarOpen ? "sidebar-open" : ""}`}>
          <button
            className="nsv-sidebarToggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? "Close Panel" : "Open Panel"}
          >
            {sidebarOpen ? "»" : "« Panel"}
          </button>

          <main className="nsv-plotCard">
            <div className="nsv-plotHead">
              <div>
                <div className="nsv-plotTitle">Tracker {frameId} — North–South (Front Elevation)</div>
                <div className="nsv-plotSub">
                  Base tick + marker + pile # at bottom. Module segment at top uses <strong>module width</strong>.
                </div>
              </div>

              <div className="nsv-miniBadges">
                <span className="nsv-miniBadge danger">Violation</span>
                <span className="nsv-miniBadge warn">Graded</span>
                <span className="nsv-miniBadge ok">OK</span>
              </div>
            </div>

            <div className="nsv-plotWrap">
              <Plot
                data={plotTraces}
                layout={{
                  autosize: true,
                  xaxis: {
                    title: "Easting (m)",
                    showgrid: true,
                    gridcolor: "rgba(2,6,23,0.08)",
                    tickformat: ",.0f",
                    separatethousands: true,
                    zeroline: false,
                  },
                  yaxis: {
                    title: "Elevation (m)",
                    showgrid: true,
                    gridcolor: "rgba(2,6,23,0.08)",
                    tickformat: ",.2f",
                    separatethousands: true,
                    zeroline: false,
                  },
                  hovermode: "closest",
                  showlegend: true,
                  legend: { orientation: "h", y: -0.18 },
                  dragmode: "pan",
                  margin: { l: 70, r: 30, t: 20, b: 70 },
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  font: { color: "rgba(15,23,42,0.92)" },
                }}
                config={{ responsive: true, scrollZoom: true, displaylogo: false }}
                useResizeHandler
                style={{ width: "100%", height: "600px" }}
              />
            </div>
          </main>

          <aside className={`nsv-sidebar ${sidebarOpen ? "open" : "closed"}`}>
            <form className="nsv-pileJump" onSubmit={handlePileJump}>
              <div className="nsv-pileJumpLabel">Go to pile (in Tracker {frameId})</div>
              <div className="nsv-pileJumpRow">
                <div className="nsv-pileJumpPrefix" aria-hidden="true">
                  {String(frameId)}.
                </div>
                <input
                  className="nsv-pileJumpInput"
                  value={pileJump}
                  onChange={(e) => setPileJump(e.target.value)}
                  inputMode="numeric"
                  placeholder="03"
                  aria-label="Enter pile number in tracker"
                />
                <button className="nsv-pileJumpBtn" type="submit">
                  Go
                </button>
              </div>
              <div className="nsv-pileJumpHint">
                Example: <strong>{String(frameId)}.03</strong> means pile <strong>3</strong> in this tracker.
              </div>
            </form>

            <div className="nsv-sidebarHeader">
              <div className="nsv-sidebarTitle">Notes</div>
              <div className="nsv-sidebarHint">
                Hover info is limited to: <strong>Pile #</strong>, <strong>Base</strong>, <strong>Top</strong>.
                <br />
                Module segment uses <strong>module width</strong> and scales by depth (northing).
              </div>
            </div>

            <div className="nsv-sidebarFooter">Tip: Switch back to East–West view for terrain + limits.</div>
          </aside>
        </div>
      </div>

      <footer className="nsv-footer">PCL Earthworks Tool • Frame Profile → North–South View</footer>
    </div>
  );
}
