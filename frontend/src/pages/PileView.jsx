import { useMemo } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import Plot from "react-plotly.js";
import "./PileView.css";

import pclLogo from "../assets/logos/pcllogo.png";
import backgroundImage from "../assets/logos/Australia-Office-2025.png";

function toPosNumber(v) {
  const n = Number(v);
  return Number.isFinite(n) && n > 0 ? n : null;
}

// Always draw the MINOR arc between a0 and a1
function arcPointsMinor(cx, cy, r, a0Deg, a1Deg, steps = 40) {
  const a0 = (a0Deg * Math.PI) / 180;
  const diffDeg = ((a1Deg - a0Deg + 540) % 360) - 180; // [-180,180]
  const a1 = ((a0Deg + diffDeg) * Math.PI) / 180;

  const xs = [];
  const ys = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const a = a0 + (a1 - a0) * t;
    xs.push(cx + r * Math.cos(a));
    ys.push(cy + r * Math.sin(a));
  }
  return { x: xs, y: ys, midAngleRad: a0 + (a1 - a0) * 0.5 };
}

export default function PileView() {
  const { pileId } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();

  const meta = useMemo(() => {
    return {
      fileName: state?.fileName || "",
      sheetName: state?.sheetName || "",
      trackerType: state?.trackerType || "flat",
    };
  }, [state]);

  const pile = state?.pile || null;
  const violation = state?.violation || null;

  // Keep this behaviour from your older code: build "Open Tracker" state
  const gradingResults = state?.gradingResults || null;

  // Read params saved from Parameters page
  const params = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("pcl_parameters") || "null") || {};
    } catch {
      return {};
    }
  }, []);

  const moduleLength = useMemo(
    () => toPosNumber(params?.moduleLength ?? state?.moduleLength ?? null),
    [params, state]
  );

  const minClearance = useMemo(
    () => toPosNumber(params?.minClearance ?? state?.minClearance ?? null),
    [params, state]
  );

  // Max tilt from horizontal (deg) with default 60
  const maxTiltAngle = useMemo(() => {
    const v = params?.maxTiltAngle ?? state?.maxTiltAngle ?? 60;
    const n = Number(v);
    if (!Number.isFinite(n)) return 60;
    return Math.min(89.9, Math.max(0.1, n));
  }, [params, state]);

  // Choose which side the module leans toward
  const moduleSide = "right"; // "right" | "left"

  // If someone refreshes / direct-opens, state is missing
  if (!pile) {
    return (
      <div className="pv-shell">
        <div className="pv-bg" aria-hidden="true">
          <img src={backgroundImage} alt="" className="pv-bgImg" />
          <div className="pv-bgOverlay" />
          <div className="pv-gridOverlay" />
        </div>

        <div className="pv-empty">
          <div className="pv-emptyCard">
            <div className="pv-emptyTitle">No pile data found</div>
            <div className="pv-emptySub">
              Please go back to <strong>Run Analysis</strong>, run grading, then open the pile again.
            </div>
            <button className="pv-btn pv-btnPrimary" onClick={() => navigate("/run-analysis")}>
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  const trackerId = Math.floor(Number(pile.pile_id));
  const pileInTracker = pile.pile_in_tracker;

  const initialElev = Number(pile.initial_elevation ?? 0);
  const finalElev = Number(pile.final_elevation ?? 0);
  const pileTop = Number(pile.total_height ?? 0);
  const change = finalElev - initialElev;

  const pileTrace = useMemo(() => ({ x: [0, 0], y: [finalElev, pileTop] }), [finalElev, pileTop]);

  // Geometry for module + arcs + clearance measurement
  const moduleGeom = useMemo(() => {
    if (!moduleLength) return null;

    const centerX = 0;
    const centerY = pileTop;

    // module upper ray angle from +x is tilt angle from horizontal
    const tilt = maxTiltAngle; // from horizontal
    const moduleUpDeg = moduleSide === "left" ? 180 - tilt : tilt;

    // underside ray (the "slanting down" side)
    const moduleDownDeg = (moduleUpDeg + 180) % 360;

    // pile underside ray: vertical down
    const pileDownDeg = 270;

    // horizontal under-ray: away from pile in the lower half-plane
    // right side => use 180° (pointing left) in lower half-plane
    // left side  => use 0° (pointing right) in lower half-plane
    const horizontalUnderDeg = moduleSide === "left" ? 0 : 180;

    // module endpoints centered at pile top
    const theta = (moduleUpDeg * Math.PI) / 180;
    const dxHalf = (moduleLength / 2) * Math.cos(theta);
    const dyHalf = (moduleLength / 2) * Math.sin(theta);

    const x1 = centerX - dxHalf;
    const y1 = centerY - dyHalf;
    const x2 = centerX + dxHalf;
    const y2 = centerY + dyHalf;

    const endLow = y1 <= y2 ? { x: x1, y: y1 } : { x: x2, y: y2 };
    const endHigh = y1 <= y2 ? { x: x2, y: y2 } : { x: x1, y: y1 };

    // arcs radii
    const rPile = Math.max(0.18, moduleLength * 0.18); // for (90-tilt)
    const rTilt = Math.max(0.22, moduleLength * 0.22); // for tilt

    const angleToHorizontal = tilt; // tilt from horizontal
    const angleToPile = 90 - tilt; // from module to vertical

    // Draw underside arcs:
    // (A) tilt arc: horizontal underside -> module underside (tilt)
    const arcTilt = arcPointsMinor(centerX, centerY, rTilt, horizontalUnderDeg, moduleDownDeg, 48);
    const labelTilt = {
      x: centerX + (rTilt * 1.1) * Math.cos(arcTilt.midAngleRad),
      y: centerY + (rTilt * 1.1) * Math.sin(arcTilt.midAngleRad),
    };

    // (B) pile arc: module underside -> pile underside (90-tilt)
    const arcPile = arcPointsMinor(centerX, centerY, rPile, moduleDownDeg, pileDownDeg, 36);
    const labelPile = {
      x: centerX + (rPile * 1.1) * Math.cos(arcPile.midAngleRad),
      y: centerY + (rPile * 1.1) * Math.sin(arcPile.midAngleRad),
    };

    // clearance from underside end to final elevation (vertical distance)
    const clearance = endLow.y - finalElev;

    return {
      centerX,
      centerY,
      xLine: [x1, x2],
      yLine: [y1, y2],
      endLow,
      endHigh,

      angleToHorizontal,
      angleToPile,

      arcTilt,
      arcPile,
      labelTilt,
      labelPile,

      clearance,
    };
  }, [moduleLength, pileTop, finalElev, moduleSide, maxTiltAngle]);

  const clearanceStatus = useMemo(() => {
    if (!moduleGeom) return { ok: true, reason: "" };
    const c = moduleGeom.clearance;
    const minC = minClearance ?? null;

    if (c < 0) return { ok: false, reason: "Module underside end goes below Final Elevation." };
    if (minC !== null && c < minC) {
      return { ok: false, reason: `Clearance is below minimum required (${minC.toFixed(3)} m).` };
    }
    return { ok: true, reason: "" };
  }, [moduleGeom, minClearance]);

  // Plot ranges to include pile + module + arcs + clearance
  const plotRanges = useMemo(() => {
    let xMin = -1.2;
    let xMax = 1.2;

    if (moduleGeom) {
      const allX = [
        ...moduleGeom.xLine,
        ...(moduleGeom.arcTilt?.x || []),
        ...(moduleGeom.arcPile?.x || []),
        moduleGeom.labelTilt.x,
        moduleGeom.labelPile.x,
        moduleGeom.endLow.x,
      ].filter((v) => Number.isFinite(v));

      const absX = Math.max(...allX.map((v) => Math.abs(v)), 0.8);
      const padX = Math.max(0.35, absX * 0.35);
      xMin = -absX - padX;
      xMax = absX + padX;
    }

    let yMin = Math.min(initialElev, finalElev, pileTop);
    let yMax = Math.max(initialElev, finalElev, pileTop);

    if (moduleGeom) {
      const allY = [
        ...moduleGeom.yLine,
        ...(moduleGeom.arcTilt?.y || []),
        ...(moduleGeom.arcPile?.y || []),
        moduleGeom.labelTilt.y,
        moduleGeom.labelPile.y,
        moduleGeom.endLow.y,
      ].filter((v) => Number.isFinite(v));
      yMin = Math.min(yMin, ...allY);
      yMax = Math.max(yMax, ...allY);
    }

    const padY = Math.max(0.35, (yMax - yMin) * 0.18);
    return { x: [xMin, xMax], y: [yMin - padY, yMax + padY] };
  }, [moduleGeom, initialElev, finalElev, pileTop]);

  // Horizontal lines for initial & final elevation
  const elevationShapes = useMemo(() => {
    const [x0, x1] = plotRanges.x;
    return [
      {
        type: "line",
        xref: "x",
        yref: "y",
        x0,
        x1,
        y0: initialElev,
        y1: initialElev,
        line: { color: "rgba(30, 136, 229, 0.95)", width: 2, dash: "dot" },
      },
      {
        type: "line",
        xref: "x",
        yref: "y",
        x0,
        x1,
        y0: finalElev,
        y1: finalElev,
        line: { color: "rgba(34, 197, 94, 0.95)", width: 2, dash: "dot" },
      },
    ];
  }, [plotRanges.x, initialElev, finalElev]);

  // Annotations including arc labels + clearance label
  const annotations = useMemo(() => {
    const [x0] = plotRanges.x;
    const same = Math.abs(initialElev - finalElev) < 1e-6;
    const initialYForLabel = same ? initialElev + 0.03 : initialElev;

    const anns = [
      {
        x: x0,
        y: initialYForLabel,
        xref: "x",
        yref: "y",
        text: "Initial Elevation",
        showarrow: false,
        xanchor: "left",
        yanchor: "bottom",
        font: { size: 12, color: "rgba(30, 136, 229, 0.95)" },
        bgcolor: "rgba(255,255,255,0.92)",
        bordercolor: "rgba(30,136,229,0.25)",
        borderwidth: 1,
        borderpad: 4,
      },
      {
        x: x0,
        y: finalElev,
        xref: "x",
        yref: "y",
        text: "Final Elevation",
        showarrow: false,
        xanchor: "left",
        yanchor: "bottom",
        font: { size: 12, color: "rgba(34, 197, 94, 0.95)" },
        bgcolor: "rgba(255,255,255,0.92)",
        bordercolor: "rgba(34,197,94,0.25)",
        borderwidth: 1,
        borderpad: 4,
      },
    ];

    if (moduleGeom) {
      // tilt label (input)
      anns.push({
        x: moduleGeom.labelTilt.x,
        y: moduleGeom.labelTilt.y,
        xref: "x",
        yref: "y",
        text: `${moduleGeom.angleToHorizontal.toFixed(0)}°`,
        showarrow: false,
        font: { size: 13, color: "rgba(123, 31, 162, 0.98)", family: "Arial Black" },
        bgcolor: "rgba(255,255,255,0.94)",
        bordercolor: "rgba(123,31,162,0.25)",
        borderwidth: 1,
        borderpad: 4,
      });

      // to pile label (computed)
      anns.push({
        x: moduleGeom.labelPile.x,
        y: moduleGeom.labelPile.y,
        xref: "x",
        yref: "y",
        text: `${moduleGeom.angleToPile.toFixed(0)}°`,
        showarrow: false,
        font: { size: 13, color: "rgba(216, 67, 21, 0.98)", family: "Arial Black" },
        bgcolor: "rgba(255,255,255,0.94)",
        bordercolor: "rgba(216,67,21,0.25)",
        borderwidth: 1,
        borderpad: 4,
      });

      // clearance label
      const midY = (moduleGeom.endLow.y + finalElev) / 2;
      const x = moduleGeom.endLow.x;

      const clearanceLabelColor = clearanceStatus.ok
        ? "rgba(2, 6, 23, 0.88)"
        : "rgba(220, 38, 38, 0.98)";
      const clearanceBorder = clearanceStatus.ok ? "rgba(2,6,23,0.14)" : "rgba(220,38,38,0.28)";

      anns.push({
        x,
        y: midY,
        xref: "x",
        yref: "y",
        text: `Clearance: ${Math.abs(moduleGeom.clearance).toFixed(3)} m`,
        showarrow: false,
        xanchor: moduleSide === "right" ? "left" : "right",
        yanchor: "middle",
        font: { size: 12, color: clearanceLabelColor, family: "Arial Black" },
        bgcolor: "rgba(255,255,255,0.95)",
        bordercolor: clearanceBorder,
        borderwidth: 1,
        borderpad: 4,
      });
    }

    return anns;
  }, [plotRanges.x, initialElev, finalElev, moduleGeom, moduleSide, clearanceStatus]);

  // Clearance measurement line (vertical) from module low end to final elevation
  const clearanceTrace = useMemo(() => {
    if (!moduleGeom) return null;

    const bad = !clearanceStatus.ok;
    const lineColor = bad ? "rgba(220, 38, 38, 0.75)" : "rgba(2, 6, 23, 0.55)";

    return {
      x: [moduleGeom.endLow.x, moduleGeom.endLow.x],
      y: [moduleGeom.endLow.y, finalElev],
      type: "scatter",
      mode: "lines+markers",
      line: { width: 3, dash: "dash", color: lineColor },
      marker: {
        size: 8,
        color: [
          bad ? "rgba(220,38,38,0.98)" : "rgba(2,6,23,0.95)",
          "rgba(34, 197, 94, 0.95)",
        ],
        line: { width: 2, color: "#ffffff" },
      },
      hovertemplate:
        "Clearance<br>" +
        `End (module): %{y[0]:.3f} m<br>` +
        `Final elev: %{y[1]:.3f} m<br>` +
        `Δ: ${Math.abs(moduleGeom.clearance).toFixed(3)} m<extra></extra>`,
      showlegend: false,
    };
  }, [moduleGeom, finalElev, clearanceStatus]);

  const moduleLineColor =
    !moduleGeom
      ? "rgba(30, 136, 229, 0.95)"
      : clearanceStatus.ok
      ? "rgba(30, 136, 229, 0.95)"
      : "rgba(220, 38, 38, 0.95)";

  // Build trackerResults like your older code so Open Tracker works
  const trackerResultsForLink = useMemo(() => {
    if (!gradingResults?.piles) return null;

    const pilesInTracker = gradingResults.piles.filter((p) => Math.floor(p.pile_id) === trackerId);
    const violationsInTracker = (gradingResults.violations || []).filter(
      (v) => Math.floor(v.pile_id) === trackerId
    );

    return {
      tracker_id: trackerId,
      tracker_type: meta.trackerType,
      piles: pilesInTracker,
      violations: violationsInTracker,
      total_cut: pilesInTracker.reduce((sum, p) => sum + (p.cut_fill > 0 ? p.cut_fill : 0), 0),
      total_fill: pilesInTracker.reduce(
        (sum, p) => sum + (p.cut_fill < 0 ? Math.abs(p.cut_fill) : 0),
        0
      ),
      constraints: gradingResults.constraints,
    };
  }, [gradingResults, trackerId, meta.trackerType]);

  return (
    <div className="pv-shell">
      <div className="pv-bg" aria-hidden="true">
        <img src={backgroundImage} alt="" className="pv-bgImg" />
        <div className="pv-bgOverlay" />
        <div className="pv-gridOverlay" />
      </div>

      <header className="pv-header">
        <div className="pv-headerInner">
          <div className="pv-brand">
            <img src={pclLogo} alt="PCL Logo" className="pv-logo" />
            <div className="pv-brandText">
              <div className="pv-brandTitle">Earthworks Analysis Tool</div>
              <div className="pv-brandSub">Pile view • details • outcomes</div>
            </div>
          </div>

          <div className="pv-headerActions">
            <Link
              to="/run-analysis"
              state={{ gradingResults: state?.gradingResults }}
              className="pv-navLink"
            >
              ← Back to Run Analysis
            </Link>

            <Link
              to={`/frame/${encodeURIComponent(trackerId)}`}
              state={{
                frameId: String(trackerId),
                fileName: meta.fileName,
                sheetName: meta.sheetName,
                trackerType: meta.trackerType,
                gradingResults: state?.gradingResults,
                trackerResults: trackerResultsForLink,
              }}
              className="pv-navLink"
              title="Open tracker side profile"
            >
              Open Tracker {trackerId} →
            </Link>
          </div>
        </div>
      </header>

      <div className="pv-main">
        <div className="pv-hero">
          <div className="pv-badge">
            <span className="pv-badgeDot" />
            Pile View
          </div>
          <h1 className="pv-h1">Pile {Number(pile.pile_id).toFixed(2)}</h1>
          <p className="pv-subtitle">
            Tracker <strong>{trackerId}</strong> • Pile <strong>{pileInTracker}</strong>
          </p>
        </div>

        {!clearanceStatus.ok && moduleGeom && minClearance && (
          <div
            className="pv-warning"
            style={{ borderColor: "rgba(220,38,38,0.45)", background: "rgba(220,38,38,0.14)" }}
          >
            <div className="pv-warningIcon">⛔</div>
            <div className="pv-warningText">
              <strong>Minimum clearance not satisfied.</strong> {clearanceStatus.reason}
              <span style={{ display: "block", marginTop: 6 }}>
                Clearance = <strong>{moduleGeom.clearance.toFixed(3)} m</strong> • Required ≥{" "}
                <strong>{Number(minClearance).toFixed(3)} m</strong>
              </span>
            </div>
          </div>
        )}

        <div className="pv-grid">
          <div className="pv-card">
            <div className="pv-cardTitle">Pile Details</div>

            <div className="pv-kv">
              <div className="pv-k">Initial Elevation</div>
              <div className="pv-v">{Number(initialElev).toFixed(3)} m</div>

              <div className="pv-k">Final Elevation</div>
              <div className="pv-v">{Number(finalElev).toFixed(3)} m</div>

              <div className="pv-k">Pile Top (Total Height)</div>
              <div className="pv-v">{Number(pileTop).toFixed(3)} m</div>

              <div className="pv-k">Module length</div>
              <div className="pv-v">{moduleLength ? `${Number(moduleLength).toFixed(3)} m` : "—"}</div>

              <div className="pv-k">Min clearance</div>
              <div className="pv-v">{minClearance ? `${Number(minClearance).toFixed(3)} m` : "—"}</div>

              <div className="pv-k">Max tilt (from horizontal)</div>
              <div className="pv-v">{Number(maxTiltAngle).toFixed(1)}°</div>

              <div className="pv-k">Angle to pile (vertical)</div>
              <div className="pv-v">{(90 - Number(maxTiltAngle)).toFixed(1)}°</div>

              {moduleGeom && (
                <>
                  <div className="pv-k">Clearance (underside end → final)</div>
                  <div
                    className="pv-v"
                    style={{ color: clearanceStatus.ok ? "inherit" : "#ff4d4d", fontWeight: 900 }}
                  >
                    {moduleGeom.clearance.toFixed(3)} m
                  </div>
                </>
              )}

              
              
            </div>
          </div>

          <div className="pv-card pv-plotCard">
            <div className="pv-cardTitle">Vertical Profile (Interactive)</div>

            <div className="pv-plotWrap">
              <Plot
                data={[
                  // pile
                  {
                    x: pileTrace.x,
                    y: pileTrace.y,
                    type: "scatter",
                    mode: "lines+markers",
                    line: { width: 6, color: violation ? "#FF4D4D" : "#FF9800" },
                    marker: { size: 10 },
                    hovertemplate: "Pile<br>Elevation: %{y:.3f} m<extra></extra>",
                    showlegend: false,
                  },

                  ...(moduleGeom
                    ? [
                        // module line
                        {
                          x: moduleGeom.xLine,
                          y: moduleGeom.yLine,
                          type: "scatter",
                          mode: "lines",
                          line: { width: 5, color: moduleLineColor },
                          hovertemplate:
                            "Module line<br>Length: " +
                            Number(moduleLength).toFixed(3) +
                            " m<br>Tilt from horizontal: " +
                            Number(maxTiltAngle).toFixed(1) +
                            "°<br>Angle to pile: " +
                            (90 - Number(maxTiltAngle)).toFixed(1) +
                            "°<extra></extra>",
                          showlegend: false,
                        },

                        // pile-top marker
                        {
                          x: [moduleGeom.centerX],
                          y: [moduleGeom.centerY],
                          type: "scatter",
                          mode: "markers",
                          marker: { size: 10, color: "#111827", line: { width: 2, color: "#ffffff" } },
                          hovertemplate: "Pile top (center)<extra></extra>",
                          showlegend: false,
                        },

                        // tilt arc (horizontal underside -> module underside)
                        {
                          x: moduleGeom.arcTilt.x,
                          y: moduleGeom.arcTilt.y,
                          type: "scatter",
                          mode: "lines",
                          line: { width: 3, color: "rgba(123, 31, 162, 0.98)" },
                          hoverinfo: "skip",
                          showlegend: false,
                        },

                        // pile arc (module underside -> pile underside)
                        {
                          x: moduleGeom.arcPile.x,
                          y: moduleGeom.arcPile.y,
                          type: "scatter",
                          mode: "lines",
                          line: { width: 3, color: "rgba(216, 67, 21, 0.98)" },
                          hoverinfo: "skip",
                          showlegend: false,
                        },
                      ]
                    : []),

                  ...(clearanceTrace ? [clearanceTrace] : []),
                ]}
                layout={{
                  margin: { l: 70, r: 24, t: 18, b: 52 },
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  font: { color: "#0f172a" },

                  xaxis: {
                    title: "",
                    showticklabels: false,
                    zeroline: false,
                    showgrid: true,
                    gridcolor: "rgba(2, 6, 23, 0.10)",
                    range: plotRanges.x,
                  },

                  yaxis: {
                    title: "Elevation (m)",
                    showgrid: true,
                    gridcolor: "rgba(2, 6, 23, 0.10)",
                    tickformat: ",.3f",
                    range: plotRanges.y,
                    // keep geometry looking correct when you zoom
                    scaleanchor: "x",
                    scaleratio: 1,
                  },

                  shapes: [...elevationShapes],
                  annotations: [...annotations],

                  showlegend: false,
                  hovermode: "closest",
                }}
                // ✅ interactive scroll zoom + zoom/pan enabled
                config={{
                  responsive: true,
                  displaylogo: false,
                  scrollZoom: true,
                  doubleClick: "reset",
                  modeBarButtonsToAdd: ["zoom2d", "pan2d", "resetScale2d", "toImage"],
                }}
                style={{ width: "100%", height: "100%" }}
              />
            </div>

            <div className="pv-plotNote">
              Scroll to zoom • Drag to pan • Double-click to reset. Tilt = angle from horizontal; angle to pile = 90° − tilt.
            </div>
          </div>
        </div>
      </div>

      <footer className="pv-footer">PCL Earthworks Tool • Run Analysis → Pile View</footer>
    </div>
  );
}
