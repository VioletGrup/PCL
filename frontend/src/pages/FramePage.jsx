import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams, useNavigate } from "react-router-dom";
import Plot from "react-plotly.js";
import "./FramePage.css";

export default function FramePage() {
  const { frameId } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();

  const [grading, setGrading] = useState(state?.trackerResults || null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [hiddenTraces, setHiddenTraces] = useState(new Set());

  const toggleTrace = (name) => {
    setHiddenTraces(prev => {
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
    console.log("FramePage mounted. State:", state);
  }, [state]);

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
      const xVals = piles.map(p => p.northing);

      // Check for inverted window (Tolerance > Range)
      const windowInverted = (minReveal + tolerance / 2) > (maxReveal - tolerance / 2);
      const toleranceImpact = tolerance;
      const availableRange = maxReveal - minReveal;

      return {
        x: xVals,
        original: piles.map(p => p.initial_elevation),
        proposed: piles.map(p => p.final_elevation),
        optimal: piles.map(p => p.total_height),
        // No Tolerance Limits (Theoretical Window - Relative to Proposed Ground)
        minLimitNoTolerance: piles.map(p => p.final_elevation + minReveal + (p.flooding_allowance || 0)),
        maxLimitNoTolerance: piles.map(p => p.final_elevation + maxReveal),
        // Final Window (Actual Grading Window - Relative to Proposed Ground)
        finalMinLimit: piles.map(p => p.final_elevation + minReveal + (p.flooding_allowance || 0) + tolerance / 2),
        finalMaxLimit: piles.map(p => p.final_elevation + maxReveal - tolerance / 2),
        windowInverted,
        toleranceImpact,
        availableRange
      };
    } catch (e) {
      console.error("Error calculating plot data:", e);
      return null;
    }
  }, [grading]);

  if (!grading) {
    return (
      <div className="fp-shell">
        <div className="fp-error">
          No grading results found. Please go back to "Run Analysis" and click "Run Grading".
          <br />
          <button className="fp-btn" onClick={() => navigate("/run-analysis")}>Go Back</button>
        </div>
      </div>
    );
  }

  return (
    <div className="fp-shell">
      <header className="fp-topbar">
        <div className="fp-left">
          <Link
            to="/run-analysis"
            state={{ gradingResults: state?.gradingResults }}
            className="fp-link"
          >
            ← Back to Plot
          </Link>
          <h1 className="fp-title">Tracker {frameId}</h1>
          <div className="fp-subtitle">
            Side view profile and grading analysis
          </div>
        </div>

        <div className="fp-meta">
          <div className="fp-chip">
            <div className="fp-chip-label">File</div>
            <div className="fp-chip-value">{meta.fileName || "—"}</div>
          </div>
          <div className="fp-chip">
            <div className="fp-chip-label">Sheet</div>
            <div className="fp-chip-value">{meta.sheetName || "—"}</div>
          </div>
          <div className="fp-chip">
            <div className="fp-chip-label">Tracker</div>
            <div className="fp-chip-value">{meta.trackerType.toUpperCase()}</div>
          </div>
          <div className="fp-chip">
            <div className="fp-chip-label">Total Cut</div>
            <div className="fp-chip-value">{grading.total_cut.toFixed(2)} m</div>
          </div>
          <div className="fp-chip">
            <div className="fp-chip-label">Total Fill</div>
            <div className="fp-chip-value">{grading.total_fill.toFixed(2)} m</div>
          </div>
        </div>
      </header>

      {plotData?.windowInverted && (
        <div className="fp-warning-banner">
          <div className="fp-warning-icon">⚠️</div>
          <div className="fp-warning-text">
            <strong>Inverted Grading Window:</strong> Your Pile Install Tolerance ({plotData.toleranceImpact}m)
            is larger than the available Reveal Range ({plotData.availableRange.toFixed(3)}m).
            This makes it mathematically impossible to satisfy the constraints.
            <em> Reduce tolerance or increase the reveal gap.</em>
          </div>
        </div>
      )}

      <div className={`fp-main-layout ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <main className="fp-content-refined">
          <button
            className="fp-sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? "Close Legend" : "Open Legend"}
          >
            {sidebarOpen ? "»" : "« Legend"}
          </button>

          <section className="fp-plot-section-full">
            {plotData && (
              <Plot
                data={[
                  {
                    x: plotData.x,
                    y: plotData.original,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Original Ground',
                    line: { color: '#8B4513', width: 2, dash: 'dot' },
                    visible: hiddenTraces.has('Original Ground') ? false : true
                  },
                  {
                    x: plotData.x,
                    y: plotData.proposed,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Proposed Ground',
                    line: { color: '#2E7D32', width: 3 },
                    fill: hiddenTraces.has('Original Ground') ? 'none' : 'tonexty',
                    fillcolor: 'rgba(46, 125, 50, 0.1)',
                    visible: hiddenTraces.has('Proposed Ground') ? false : true
                  },
                  {
                    x: plotData.x,
                    y: plotData.optimal,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Optimal Line (Pile Top)',
                    line: { color: '#000000', width: 2 },
                    marker: { size: 6, color: '#000000' },
                    visible: hiddenTraces.has('Optimal Line (Pile Top)') ? false : true
                  },
                  // Final Limits
                  {
                    x: plotData.x,
                    y: plotData.finalMaxLimit,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Final Max Limit (With Tolerance)',
                    line: { color: '#D32F2F', width: 2 },
                    visible: hiddenTraces.has('Final Max Limit (With Tolerance)') ? false : true
                  },
                  {
                    x: plotData.x,
                    y: plotData.finalMinLimit,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Final Min Limit (With Tolerance)',
                    line: { color: '#1976D2', width: 2 },
                    visible: hiddenTraces.has('Final Min Limit (With Tolerance)') ? false : true
                  },
                  // Dashed Limits
                  {
                    x: plotData.x,
                    y: plotData.maxLimitNoTolerance,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Max Limit (No Tolerance)',
                    line: { color: '#D32F2F', width: 4, dash: 'dash' },
                    visible: hiddenTraces.has('Max Limit (No Tolerance)') ? false : true
                  },
                  {
                    x: plotData.x,
                    y: plotData.minLimitNoTolerance,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Min Limit (No Tolerance)',
                    line: { color: '#1976D2', width: 4, dash: 'dash' },
                    visible: hiddenTraces.has('Min Limit (No Tolerance)') ? false : true
                  },
                  // Labels
                  {
                    x: plotData.x,
                    y: plotData.optimal.map(y => y + 0.15),
                    type: 'scatter',
                    mode: 'text',
                    text: grading.piles.map(p => `P${p.pile_in_tracker}`),
                    textposition: 'top center',
                    textfont: { size: 10, color: '#424242' },
                    showlegend: false,
                    hoverinfo: 'skip',
                    visible: (hiddenTraces.has('Optimal Line (Pile Top)') || hiddenTraces.has('Piles')) ? false : true
                  },
                  // Dummy traces for legend icons
                  {
                    x: [null], y: [null],
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Pile: Violation (Remaining)',
                    line: { color: '#FF4D4D', width: 4 },
                    visible: hiddenTraces.has('Pile: Violation (Remaining)') ? false : true
                  },
                  {
                    x: [null], y: [null],
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Pile: Graded (Fixed)',
                    line: { color: '#FF9800', width: 4 },
                    visible: hiddenTraces.has('Pile: Graded (Fixed)') ? false : true
                  },
                  {
                    x: [null], y: [null],
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Pile: OK',
                    line: { color: '#424242', width: 4 },
                    visible: hiddenTraces.has('Pile: OK') ? false : true
                  },
                  // Actual pile posts
                  ...grading.piles.map((pile) => {
                    const isViolation = grading.violations?.some(v => v.pile_id === pile.pile_id);
                    const isGraded = Math.abs(pile.cut_fill) > 0.0001;

                    let color = '#424242';
                    let traceName = 'Pile: OK';
                    if (isViolation) {
                      color = '#FF4D4D';
                      traceName = 'Pile: Violation (Remaining)';
                    } else if (isGraded) {
                      color = '#FF9800';
                      traceName = 'Pile: Graded (Fixed)';
                    }

                    return {
                      x: [pile.northing, pile.northing],
                      y: [pile.final_elevation, pile.total_height],
                      type: 'scatter',
                      mode: 'lines',
                      line: { color, width: 4 },
                      showlegend: false,
                      hoverinfo: 'skip',
                      visible: hiddenTraces.has(traceName) ? false : true
                    };
                  })
                ]}
                layout={{
                  title: `Tracker ${frameId} - Side View Profile`,
                  xaxis: { title: 'Northing (m)', showgrid: true, gridcolor: '#f0f0f0' },
                  yaxis: { title: 'Elevation (m)', scaleanchor: "x", scaleratio: 1, showgrid: true, gridcolor: '#f0f0f0' },
                  hovermode: 'closest',
                  showlegend: false,
                  dragmode: 'pan',
                  margin: { l: 60, r: 40, t: 60, b: 60 },
                  paper_bgcolor: '#ffffff',
                  plot_bgcolor: '#ffffff',
                }}
                config={{ responsive: true, scrollZoom: true, displaylogo: false }}
                style={{ width: '100%', height: '100%' }}
              />
            )}
          </section>

          {grading.violations && grading.violations.length > 0 && (
            <div className="fp-violations-overlay">
              <h3 className="fp-violations-title">⚠️ Violations</h3>
              <ul className="fp-violations-list">
                {grading.violations.map((v, i) => (
                  <li key={i}>P{v.pile_id}: {v.type} ({v.value.toFixed(3)}m)</li>
                ))}
              </ul>
            </div>
          )}
        </main>

        <aside className={`fp-sidebar-right ${sidebarOpen ? 'open' : 'closed'}`}>
          <div className="fp-sidebar-header">
            <h3 className="fp-sidebar-title">Legend</h3>
            <div className="fp-sidebar-hint">Tip: Click on names in the plot legend to hide/show lines</div>
          </div>

          <div className="fp-legend-list">
            <div className="fp-legend-group">
              <h4 className="fp-group-title">Piles</h4>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Pile: OK') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Pile: OK')}
              >
                <span className="fp-marker pile-ok"></span>
                <span>Pile: OK</span>
              </div>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Pile: Graded (Fixed)') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Pile: Graded (Fixed)')}
              >
                <span className="fp-marker pile-graded"></span>
                <span>Pile: Graded (Fixed)</span>
              </div>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Pile: Violation (Remaining)') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Pile: Violation (Remaining)')}
              >
                <span className="fp-marker pile-violation"></span>
                <span>Pile: Violation</span>
              </div>
            </div>

            <div className="fp-legend-group">
              <h4 className="fp-group-title">Limits</h4>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Max Limit (No Tolerance)') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Max Limit (No Tolerance)')}
              >
                <span className="fp-line limit-max-dash"></span>
                <span>Max Limit (No Tol.)</span>
              </div>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Min Limit (No Tolerance)') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Min Limit (No Tolerance)')}
              >
                <span className="fp-line limit-min-dash"></span>
                <span>Min Limit (No Tol.)</span>
              </div>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Final Max Limit (With Tolerance)') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Final Max Limit (With Tolerance)')}
              >
                <span className="fp-line limit-max-solid"></span>
                <span>Final Max (With Tol.)</span>
              </div>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Final Min Limit (With Tolerance)') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Final Min Limit (With Tolerance)')}
              >
                <span className="fp-line limit-min-solid"></span>
                <span>Final Min (With Tol.)</span>
              </div>
            </div>

            <div className="fp-legend-group">
              <h4 className="fp-group-title">Terrain</h4>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Original Ground') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Original Ground')}
              >
                <span className="fp-line original-ground"></span>
                <span>Original Ground</span>
              </div>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Proposed Ground') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Proposed Ground')}
              >
                <span className="fp-line proposed-ground"></span>
                <span>Proposed Ground</span>
              </div>
              <div
                className={`fp-legend-item ${hiddenTraces.has('Optimal Line (Pile Top)') ? 'hidden' : ''}`}
                onClick={() => toggleTrace('Optimal Line (Pile Top)')}
              >
                <span className="fp-line optimal-line"></span>
                <span>Optimal Line</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}