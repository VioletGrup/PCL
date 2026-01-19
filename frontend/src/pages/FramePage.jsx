import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams, useNavigate } from "react-router-dom";
import Plot from "react-plotly.js";
import "./FramePage.css";

export default function FramePage() {
  const { frameId } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();

  const [grading, setGrading] = useState(state?.trackerResults || null);

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

      <main className="fp-content-refined">
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
                  line: { color: '#8B4513', width: 2, dash: 'dot' }
                },
                {
                  x: plotData.x,
                  y: plotData.proposed,
                  type: 'scatter',
                  mode: 'lines',
                  name: 'Proposed Ground',
                  line: { color: '#2E7D32', width: 3 },
                  fill: 'tonexty',
                  fillcolor: 'rgba(46, 125, 50, 0.1)'
                },
                {
                  x: plotData.x,
                  y: plotData.optimal,
                  type: 'scatter',
                  mode: 'lines+markers',
                  name: 'Optimal Line (Pile Top)',
                  line: { color: '#000000', width: 2 },
                  marker: { size: 6, color: '#000000' }
                },
                // Final Limits (Solid - Actual Grading Window)
                {
                  x: plotData.x,
                  y: plotData.finalMaxLimit,
                  type: 'scatter',
                  mode: 'lines',
                  name: 'Final Max Limit (With Tolerance)',
                  line: { color: '#D32F2F', width: 2, dash: 'solid' }
                },
                {
                  x: plotData.x,
                  y: plotData.finalMinLimit,
                  type: 'scatter',
                  mode: 'lines',
                  name: 'Final Min Limit (With Tolerance)',
                  line: { color: '#1976D2', width: 2, dash: 'solid' }
                },
                // No Tolerance Limits (Dashed - Theoretical Window)
                {
                  x: plotData.x,
                  y: plotData.maxLimitNoTolerance,
                  type: 'scatter',
                  mode: 'lines',
                  name: 'Max Limit (No Tolerance)',
                  line: { color: '#D32F2F', width: 4, dash: 'dash' },
                },
                {
                  x: plotData.x,
                  y: plotData.minLimitNoTolerance,
                  type: 'scatter',
                  mode: 'lines',
                  name: 'Min Limit (No Tolerance)',
                  line: { color: '#1976D2', width: 4, dash: 'dash' },
                },
                // Pile Labels
                {
                  x: plotData.x,
                  y: plotData.optimal.map(y => y + 0.15),
                  type: 'scatter',
                  mode: 'text',
                  text: grading.piles.map(p => `P${p.pile_in_tracker}`),
                  textposition: 'top center',
                  textfont: { size: 10, color: '#424242' },
                  showlegend: false,
                  hoverinfo: 'skip'
                },
                // Dummy traces for pile legend
                {
                  x: [null], y: [null],
                  type: 'scatter',
                  mode: 'lines',
                  name: 'Pile: Needs Grading / Violation',
                  line: { color: '#FF9800', width: 4 }
                },
                {
                  x: [null], y: [null],
                  type: 'scatter',
                  mode: 'lines',
                  name: 'Pile: OK',
                  line: { color: '#424242', width: 4 }
                },
                // Actual pile posts
                ...grading.piles.map((pile) => {
                  const isViolation = grading.violations?.some(v => v.pile_id === pile.pile_id);
                  const isGraded = Math.abs(pile.cut_fill) > 0.0001;
                  // Simplified: Orange if graded or violation, else Grey
                  const color = (isGraded || isViolation) ? '#FF9800' : '#424242';

                  return {
                    x: [pile.northing, pile.northing],
                    y: [pile.final_elevation, pile.total_height],
                    type: 'scatter',
                    mode: 'lines',
                    line: { color, width: 4 },
                    showlegend: false,
                    hoverinfo: 'skip'
                  };
                })
              ]}
              layout={{
                title: `Tracker ${frameId} - Side View Profile`,
                xaxis: { title: 'Northing (m)', showgrid: true, gridcolor: '#f0f0f0' },
                yaxis: { title: 'Elevation (m)', scaleanchor: "x", scaleratio: 1, showgrid: true, gridcolor: '#f0f0f0' },
                hovermode: 'closest',
                showlegend: true,
                legend: {
                  x: 1,
                  xanchor: 'right',
                  y: 1,
                  bgcolor: 'rgba(255, 255, 255, 0.8)',
                  bordercolor: '#e8eaf2',
                  borderwidth: 1
                },
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
    </div>
  );
}