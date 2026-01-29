// FramePage.jsx
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams, useNavigate } from "react-router-dom";
import Plot from "react-plotly.js";
import "./FramePage.css";

import pclLogo from "../assets/logos/pcllogo.png";
import backgroundImage from "../assets/logos/Australia-Office-2025.png";

export default function FramePage() {
  const { frameId } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();

  const [grading, setGrading] = useState(state?.trackerResults || null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [hiddenTraces, setHiddenTraces] = useState(new Set(["Angle Break"]));

  // jump to pile (by pile_in_tracker, not pile_id)
  const [pileJump, setPileJump] = useState("");

  const toggleTrace = (name) => {
    setHiddenTraces((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const meta = useMemo(() => {
    return {
      fileName: state?.fileName || "",
      sheetName: state?.sheetName || "",
      trackerType: state?.trackerType || "flat",
    };
  }, [state]);

  useEffect(() => {
    console.log("FramePage state changed. State:", state);
    // Only sync grading if we have new tracker results
    // This prevents clearing grading when other state changes occur
    if (state?.trackerResults) {
      setGrading(prevGrading => {
        // Only update if the tracker_id changed or if we don't have grading yet
        if (!prevGrading || prevGrading.tracker_id !== state.trackerResults.tracker_id) {
          return state.trackerResults;
        }
        return prevGrading;
      });
    }
  }, [state]);

  const handlePileJump = (e) => {
    e.preventDefault();

    // Accept "09", "9", "P09", "p9"
    const raw = String(pileJump || "").trim().replace(/^p/i, "");
    if (!raw) return;

    const pileInTrackerNum = Number(raw);
    if (!Number.isFinite(pileInTrackerNum) || !Number.isInteger(pileInTrackerNum) || pileInTrackerNum <= 0) return;

    // Find pile by pile_in_tracker within THIS tracker results
    const pileObj =
      grading?.piles?.find((p) => Number(p.pile_in_tracker) === pileInTrackerNum) || null;

    if (!pileObj) return;

    // Find matching violation (PileView reads state.violation)
    const violationObj =
      grading?.violations?.find((v) => Number(v.pile_id) === Number(pileObj.pile_id)) || null;

    // your app route is /pile/:pileId (e.g. /pile/12.03)
    navigate(`/pile/${encodeURIComponent(String(pileObj.pile_id))}`, {
      state: {
        ...state,
        pile: pileObj,
        violation: violationObj,
      },
    });
  };

  // Prepare plot data
  const plotData = useMemo(() => {
    if (!grading || !grading.piles) return null;

    try {
      const piles = [...grading.piles];
      piles.sort((a, b) => a.pile_in_tracker - b.pile_in_tracker);

      const constraints = grading.constraints || {};
      const minReveal = parseFloat(constraints.min_reveal_height);
      const maxReveal = parseFloat(constraints.max_reveal_height);

      const tolerance = parseFloat(constraints.pile_install_tolerance || 0);
      const xVals = piles.map((p) => p.northing);

      // Check for inverted window (Tolerance > Range)
      const windowInverted = minReveal + tolerance / 2 > maxReveal - tolerance / 2;
      const toleranceImpact = tolerance;
      const availableRange = maxReveal - minReveal;

      // Angle Break Highlight Logic (Round 3)
      const angleBreakRoofX = [];
      const angleBreakRoofY = [];
      const angleBreakTextX = [];
      const angleBreakTextY = [];
      const angleBreakTextVal = [];

      // Check if this is a terrain tracker
      const isTerrain = meta.trackerType === 'xtr' || meta.trackerType === 'terrain';

      if (isTerrain && piles.length > 0) {
        // We need indices, so iterate manually
        for (let i = 0; i < piles.length; i++) {
          const p = piles[i];

          if (p.final_degree_break && p.final_degree_break > 0.001) {
            const x = p.northing;
            const y = p.total_height;
            const lift = 0.02; // Vertical lift above the optimal line

            // 1. Left Highlight (incoming segment)
            if (i > 0) {
              const prev = piles[i - 1];
              const prevX = prev.northing;
              const prevY = prev.total_height;
              const dxTotal = Math.abs(x - prevX);

              // Use 20% of inter-pile distance for segment, 5% for gap
              const segLen = dxTotal * 0.03;
              const gap = dxTotal * 0.005;

              if (segLen > 0.001) {
                // Slope
                const m = (y - prevY) / (x - prevX);

                const xEnd = x - gap;
                const yEnd = y - (gap * m) + lift;

                const xStart = x - gap - segLen;
                const yStart = y - ((gap + segLen) * m) + lift;

                angleBreakRoofX.push(xStart, xEnd, null);
                angleBreakRoofY.push(yStart, yEnd, null);
              }
            }

            // 2. Right Highlight (outgoing segment)
            if (i < piles.length - 1) {
              const next = piles[i + 1];
              const nextX = next.northing;
              const nextY = next.total_height;
              const dxTotal = Math.abs(nextX - x);

              const segLen = dxTotal * 0.03;
              const gap = dxTotal * 0.005;

              if (segLen > 0.001) {
                const m = (nextY - y) / (nextX - x);

                const xStart = x + gap;
                const yStart = y + (gap * m) + lift;

                const xEnd = x + gap + segLen;
                const yEnd = y + ((gap + segLen) * m) + lift;

                angleBreakRoofX.push(xStart, xEnd, null);
                angleBreakRoofY.push(yStart, yEnd, null);
              }
            }

            // Text coordinate (above pile)
            angleBreakTextX.push(x);
            angleBreakTextY.push(y + 0.1); // Slightly above line
            angleBreakTextVal.push(p.final_degree_break.toFixed(2));
          }
        }
      }

      return {
        x: xVals,
        original: piles.map((p) => p.initial_elevation),
        proposed: piles.map((p) => p.final_elevation),
        optimal: piles.map((p) => p.total_height),
        // No Tolerance Limits (Theoretical Window - Relative to Proposed Ground)
        minLimitNoTolerance: piles.map((p) => p.final_elevation + minReveal + (p.flooding_allowance || 0)),
        maxLimitNoTolerance: piles.map((p) => p.final_elevation + maxReveal),
        // Final Window (Actual Grading Window - Relative to Proposed Ground)
        finalMinLimit: piles.map((p) => p.final_elevation + minReveal + (p.flooding_allowance || 0) + tolerance / 2),
        finalMaxLimit: piles.map((p) => p.final_elevation + maxReveal - tolerance / 2),
        windowInverted,
        toleranceImpact,
        availableRange,
        // Angle break data
        angleBreakRoofX,
        angleBreakRoofY,
        angleBreakTextX,
        angleBreakTextY,
        angleBreakTextVal,
        isTerrain,
      };
    } catch (e) {
      console.error("Error calculating plot data:", e);
      console.error("Stack trace:", e.stack);
      console.error("grading:", grading);
      console.error("meta.trackerType:", meta.trackerType);
      return null;
    }
  }, [grading, meta.trackerType]);

  if (!grading) {
    return (
      <div className="fp-shell">
        {/* Background */}
        <div className="fp-bg" aria-hidden="true">
          <img src={backgroundImage} alt="" className="fp-bgImg" />
          <div className="fp-bgOverlay" />
          <div className="fp-gridOverlay" />
        </div>

        <div className="fp-empty">
          <div className="fp-emptyCard">
            <div className="fp-emptyTitle">No grading results found</div>
            <div className="fp-emptySub">
              Please go back to <strong>Run Analysis</strong> and click <strong>Run Grading</strong>.
            </div>
            <button className="fp-btn fp-btnPrimary" onClick={() => navigate("/run-analysis")}>
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Determine if we should show extra terrain metrics
  const isTerrain = meta.trackerType === "xtr" || meta.trackerType === "terrain";

  return (
    <div className="fp-shell">
      {/* Background */}
      <div className="fp-bg" aria-hidden="true">
        <img src={backgroundImage} alt="" className="fp-bgImg" />
        <div className="fp-bgOverlay" />
        <div className="fp-gridOverlay" />
      </div>

      {/* Header */}
      <header className="fp-header">
        <div className="fp-headerInner">
          <div className="fp-brand">
            <img src={pclLogo} alt="PCL Logo" className="fp-logo" />
            <div className="fp-brandText">
              <div className="fp-brandTitle">Earthworks Analysis Tool</div>
              <div className="fp-brandSub">Tracker side profile • constraints window • pile outcomes</div>
            </div>
          </div>

          <div className="fp-headerActions">
            <Link to="/run-analysis" state={{ gradingResults: state?.gradingResults, trackerType: meta.trackerType }} className="fp-navLink">
              ← Back to Plot
            </Link>

            <div className="fp-stepPill" title="You are viewing the frame profile">
              <span className="fp-stepDot" />
              Frame View
            </div>
          </div>
        </div>
      </header>

      {/* Meta strip */}
      <div className="fp-main">
        <div className="fp-hero">
          <div className="fp-badge">
            <span className="fp-badgeDot" />
            Tracker Profile
          </div>
          <h1 className="fp-h1">Tracker {frameId}</h1>
          <p className="fp-subtitle">Side view profile and grading analysis.</p>
        </div>

        <div className="fp-metaRow">
          <div className="fp-chip">
            <div className="fp-chipLabel">File</div>
            <div className="fp-chipValue">{meta.fileName || "—"}</div>
          </div>
          <div className="fp-chip">
            <div className="fp-chipLabel">Sheet</div>
            <div className="fp-chipValue">{meta.sheetName || "—"}</div>
          </div>
          <div className="fp-chip">
            <div className="fp-chipLabel">Tracker</div>
            <div className="fp-chipValue">{meta.trackerType.toUpperCase()}</div>
          </div>
          <div className="fp-chip">
            <div className="fp-chipLabel">Total Cut</div>
            <div className="fp-chipValue">{grading.total_cut.toFixed(2)} m</div>
          </div>
          <div className="fp-chip">
            <div className="fp-chipLabel">Total Fill</div>
            <div className="fp-chipValue">{grading.total_fill.toFixed(2)} m</div>
          </div>

          {/* ✅ Terrain Specific Metrics */}
          {(() => {
            if (!isTerrain) return null;

            // Try getting metrics from the direct grading result (single tracker grading)
            let north = grading.north_wing_deflection;
            let south = grading.south_wing_deflection;

            // Fallback: Try getting them from project-wide results (project grading)
            if (north === undefined || south === undefined) {
              const metrics = state?.gradingResults?.tracker_metrics?.[frameId] || state?.gradingResults?.tracker_metrics?.[Number(frameId)];
              if (metrics) {
                north = metrics.north_wing_deflection;
                south = metrics.south_wing_deflection;
              }
            }

            return (
              <>
                {north !== undefined && (
                  <div className="fp-chip">
                    <div className="fp-chipLabel">North Deflect</div>
                    <div className="fp-chipValue">{Number(north).toFixed(2)}°</div>
                  </div>
                )}
                {south !== undefined && (
                  <div className="fp-chip">
                    <div className="fp-chipLabel">South Deflect</div>
                    <div className="fp-chipValue">{Number(south).toFixed(2)}°</div>
                  </div>
                )}
              </>
            );
          })()}
        </div>

        {plotData?.windowInverted && (
          <div className="fp-warning">
            <div className="fp-warningIcon">⚠️</div>
            <div className="fp-warningText">
              <strong>Inverted Grading Window:</strong> Your Pile Install Tolerance ({plotData.toleranceImpact}m) is larger
              than the available Reveal Range ({plotData.availableRange.toFixed(3)}m). This makes it mathematically
              impossible to satisfy the constraints. <em>Reduce tolerance or increase the reveal gap.</em>
            </div>
          </div>
        )}

        <div className={`fp-workspace ${sidebarOpen ? "sidebar-open" : ""}`}>
          {/* Sidebar toggle (keeps same behaviour) */}
          <button
            className="fp-sidebarToggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? "Close Legend" : "Open Legend"}
          >
            {sidebarOpen ? "»" : "« Legend"}
          </button>

          {/* Plot card */}
          <main className="fp-plotCard">
            <div className="fp-plotHead">
              <div>
                <div className="fp-plotTitle">Tracker {frameId} — Side View Profile</div>
                <div className="fp-plotSub">Use the legend (right) to hide/show overlays. Drag to pan, scroll to zoom.</div>
              </div>

              <div className="fp-miniBadges">
                <span className="fp-miniBadge danger">Violation</span>
                <span className="fp-miniBadge warn">Graded</span>
                <span className="fp-miniBadge ok">OK</span>
              </div>
            </div>

            <div className="fp-plotWrap">
              {plotData && (
                <Plot
                  key={`plot-${frameId}`}
                  data={[
                    {
                      x: plotData.x,
                      y: plotData.original,
                      type: "scatter",
                      mode: "lines",
                      name: "Original Ground",
                      line: { color: "#8B4513", width: 2, dash: "dot" },
                      visible: hiddenTraces.has("Original Ground") ? "legendonly" : true,
                    },
                    {
                      x: plotData.x,
                      y: plotData.proposed,
                      type: "scatter",
                      mode: "lines",
                      name: "Proposed Ground",
                      line: { color: "#2E7D32", width: 3 },
                      fill: hiddenTraces.has("Original Ground") ? "none" : "tonexty",
                      fillcolor: "rgba(46, 125, 50, 0.10)",
                      visible: hiddenTraces.has("Proposed Ground") ? "legendonly" : true,
                    },
                    {
                      x: plotData.x,
                      y: plotData.optimal,
                      type: "scatter",
                      mode: "lines+markers",
                      name: "Optimal Line (Pile Top)",
                      line: { color: "#000000", width: 2 },
                      marker: { size: 6, color: "#000000" },
                      visible: hiddenTraces.has("Optimal Line (Pile Top)") ? "legendonly" : true,
                    },
                    // Final Limits
                    {
                      x: plotData.x,
                      y: plotData.finalMaxLimit,
                      type: "scatter",
                      mode: "lines",
                      name: "Final Max Limit (With Tolerance)",
                      line: { color: "#D32F2F", width: 2, dash: "dash" },
                      visible: hiddenTraces.has("Final Max Limit (With Tolerance)") ? "legendonly" : true,
                    },
                    {
                      x: plotData.x,
                      y: plotData.finalMinLimit,
                      type: "scatter",
                      mode: "lines",
                      name: "Final Min Limit (With Tolerance)",
                      line: { color: "#1976D2", width: 2, dash: "dash" },
                      visible: hiddenTraces.has("Final Min Limit (With Tolerance)") ? "legendonly" : true,
                    },
                    // Dashed Limits
                    {
                      x: plotData.x,
                      y: plotData.maxLimitNoTolerance,
                      type: "scatter",
                      mode: "lines",
                      name: "Max Limit (No Tolerance)",
                      line: { color: "rgba(255, 152, 0, 0.5)", width: 2, dash: "dot" },
                      visible: hiddenTraces.has("Max Limit (No Tolerance)") ? "legendonly" : true,
                    },
                    {
                      x: plotData.x,
                      y: plotData.minLimitNoTolerance,
                      type: "scatter",
                      mode: "lines",
                      name: "Min Limit (No Tolerance)",
                      line: { color: "rgba(0, 188, 212, 0.5)", width: 2, dash: "dot" },
                      visible: hiddenTraces.has("Min Limit (No Tolerance)") ? "legendonly" : true,
                    },
                    // Labels
                    {
                      x: plotData.x,
                      y: plotData.optimal.map((y) => y + 0.15),
                      type: "scatter",
                      mode: "text",
                      text: grading.piles.map((p) => `P${p.pile_in_tracker}`),
                      textposition: "top center",
                      textfont: { size: 10, color: "#424242" },
                      showlegend: false,
                      hoverinfo: "skip",
                      visible:
                        hiddenTraces.has("Optimal Line (Pile Top)") || hiddenTraces.has("Piles") ? "legendonly" : true,
                    },
                    // ✅ Angle Break Traces (Roof + Text)
                    ...(plotData.isTerrain && plotData.angleBreakRoofX.length > 0
                      ? [
                        {
                          x: plotData.angleBreakRoofX,
                          y: plotData.angleBreakRoofY,
                          type: "scatter",
                          mode: "lines",
                          name: "Angle Break",
                          line: { color: "#7B1FA2", width: 2 }, // Purple, width 2
                          connectgaps: false,
                          visible: hiddenTraces.has("Angle Break") ? "legendonly" : true,
                          hoverinfo: "skip",
                        },
                        {
                          x: plotData.angleBreakTextX,
                          y: plotData.angleBreakTextY,
                          type: "scatter",
                          mode: "text",
                          text: plotData.angleBreakTextVal,
                          textfont: { size: 9, color: "#7B1FA2", weight: "bold" },
                          name: "Angle Break Value", // grouped logically
                          visible: hiddenTraces.has("Angle Break") ? "legendonly" : true,
                          showlegend: false,
                          hoverinfo: "skip",
                        },
                      ]
                      : []),

                    // Dummy traces for legend icons
                    {
                      x: [null],
                      y: [null],
                      type: "scatter",
                      mode: "lines",
                      name: "Pile: Violation (Remaining)",
                      line: { color: "#FF4D4D", width: 4 },
                      visible: hiddenTraces.has("Pile: Violation (Remaining)") ? "legendonly" : true,
                    },
                    {
                      x: [null],
                      y: [null],
                      type: "scatter",
                      mode: "lines",
                      name: "Pile: Graded (Fixed)",
                      line: { color: "#FF9800", width: 4 },
                      visible: hiddenTraces.has("Pile: Graded (Fixed)") ? "legendonly" : true,
                    },
                    {
                      x: [null],
                      y: [null],
                      type: "scatter",
                      mode: "lines",
                      name: "Pile: OK",
                      line: { color: "#424242", width: 4 },
                      visible: hiddenTraces.has("Pile: OK") ? "legendonly" : true,
                    },
                    // Actual pile posts
                    ...grading.piles.map((pile) => {
                      const isViolation = grading.violations?.some((v) => v.pile_id === pile.pile_id);
                      const isGraded = Math.abs(pile.cut_fill) > 0.0001;

                      let color = "#424242";
                      let traceName = "Pile: OK";
                      if (isViolation) {
                        color = "#FF4D4D";
                        traceName = "Pile: Violation (Remaining)";
                      } else if (isGraded) {
                        color = "#FF9800";
                        traceName = "Pile: Graded (Fixed)";
                      }

                      return {
                        x: [pile.northing, pile.northing],
                        y: [pile.final_elevation, pile.total_height],
                        type: "scatter",
                        mode: "lines",
                        line: { color, width: 4 },
                        showlegend: false,
                        hoverinfo: "skip",
                        visible: hiddenTraces.has(traceName) ? "legendonly" : true,
                      };
                    }),
                  ]}
                  layout={{
                    title: `Tracker ${frameId} - Side View Profile`,
                    xaxis: {
                      title: "Northing (m)",
                      showgrid: true,
                      gridcolor: "rgba(255,255,255,0.10)",
                      tickformat: ",.0f",
                      separatethousands: true,
                    },
                    yaxis: {
                      title: "Elevation (m)",
                      scaleanchor: "x",
                      scaleratio: 1,
                      showgrid: true,
                      gridcolor: "rgba(255,255,255,0.10)",
                      tickformat: ",.2f",
                      separatethousands: true,
                    },
                    hovermode: "closest",
                    showlegend: false,
                    dragmode: "pan",
                    margin: { l: 70, r: 30, t: 60, b: 60 },

                    // Transparent so glass card shows
                    paper_bgcolor: "rgba(0,0,0,0)",
                    plot_bgcolor: "rgba(0,0,0,0)",
                    font: { color: "rgba(255,255,255,0.92)" },
                    // Maintain UI state during re-renders
                    uirevision: frameId,
                  }}
                  config={{ responsive: true, scrollZoom: true, displaylogo: false }}
                  style={{ width: "100%", height: "100%" }}
                />
              )}
            </div>

            {grading.violations && grading.violations.length > 0 && (
              <div className="fp-violationsOverlay">
                <div className="fp-violationsTitle">⚠️ Violations</div>
                <ul className="fp-violationsList">
                  {grading.violations.map((v, i) => (
                    <li key={i}>
                      P{v.pile_id}: {v.type} ({v.value.toFixed(3)}m)
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </main>

          {/* Legend sidebar (same toggling logic as your code) */}
          <aside className={`fp-sidebar ${sidebarOpen ? "open" : "closed"}`}>
            {/* ✅ NEW: jump box */}
            <form className="fp-pileJump" onSubmit={handlePileJump}>
              <div className="fp-pileJumpLabel">Go to pile (in Tracker {frameId})</div>
              <div className="fp-pileJumpRow">
                <div className="fp-pileJumpPrefix" aria-hidden="true">
                  {String(frameId)}.
                </div>
                <input
                  className="fp-pileJumpInput"
                  value={pileJump}
                  onChange={(e) => setPileJump(e.target.value)}
                  inputMode="numeric"
                  placeholder="03"
                  aria-label="Enter pile number in tracker"
                />
                <button className="fp-pileJumpBtn" type="submit">
                  Go
                </button>
              </div>
              <div className="fp-pileJumpHint">
                Example: <strong>{String(frameId)}.03</strong> means pile <strong>3</strong> in this tracker.
              </div>
            </form>

            <div className="fp-sidebarHeader">
              <div className="fp-sidebarTitle">Legend</div>
              <div className="fp-sidebarHint">Click items to hide/show traces.</div>
            </div>

            <div className="fp-legendList">
              {/* Angle Break at top - hidden by default */}
              {isTerrain && (
                <div className="fp-legendGroup">
                  <div className="fp-groupTitle">XTR Metrics</div>
                  <div
                    className={`fp-legendItem ${hiddenTraces.has("Angle Break") ? "hidden" : ""}`}
                    onClick={() => toggleTrace("Angle Break")}
                    role="button"
                    tabIndex={0}
                  >
                    <span
                      className="fp-line"
                      style={{
                        height: "3px",
                        backgroundColor: "#7B1FA2",
                      }}
                    />
                    <span>Angle Break</span>
                  </div>
                </div>
              )}

              <div className="fp-legendGroup">
                <div className="fp-groupTitle">Piles</div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Pile: OK") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Pile: OK")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-marker pile-ok" />
                  <span>Pile: OK</span>
                </div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Pile: Graded (Fixed)") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Pile: Graded (Fixed)")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-marker pile-graded" />
                  <span>Pile: Graded (Fixed)</span>
                </div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Pile: Violation (Remaining)") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Pile: Violation (Remaining)")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-marker pile-violation" />
                  <span>Pile: Violation</span>
                </div>
              </div>

              <div className="fp-legendGroup">
                <div className="fp-groupTitle">Limits</div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Max Limit (No Tolerance)") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Max Limit (No Tolerance)")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-line limit-max-dash" />
                  <span>Max Limit (No Tol.)</span>
                </div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Min Limit (No Tolerance)") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Min Limit (No Tolerance)")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-line limit-min-dash" />
                  <span>Min Limit (No Tol.)</span>
                </div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Final Max Limit (With Tolerance)") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Final Max Limit (With Tolerance)")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-line limit-max-solid" />
                  <span>Final Max (With Tol.)</span>
                </div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Final Min Limit (With Tolerance)") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Final Min Limit (With Tolerance)")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-line limit-min-solid" />
                  <span>Final Min (With Tol.)</span>
                </div>
              </div>

              <div className="fp-legendGroup">
                <div className="fp-groupTitle">Terrain</div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Original Ground") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Original Ground")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-line original-ground" />
                  <span>Original Ground</span>
                </div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Proposed Ground") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Proposed Ground")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-line proposed-ground" />
                  <span>Proposed Ground</span>
                </div>

                <div
                  className={`fp-legendItem ${hiddenTraces.has("Optimal Line (Pile Top)") ? "hidden" : ""}`}
                  onClick={() => toggleTrace("Optimal Line (Pile Top)")}
                  role="button"
                  tabIndex={0}
                >
                  <span className="fp-line optimal-line" />
                  <span>Optimal Line</span>
                </div>
              </div>

              <div className="fp-sidebarFooter">Tip: You can also zoom/pan directly on the plot for detailed inspection.</div>
            </div>
          </aside>
        </div>
      </div>

      <footer className="fp-footer">PCL Earthworks Tool • Run Analysis → Frame Profile</footer>
    </div>
  );
}
