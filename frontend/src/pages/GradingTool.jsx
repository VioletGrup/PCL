import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import "./GradingTool.css";

export default function GradingTool() {
  const [status, setStatus] = useState("idle"); // idle | generating | ready | error
  const [error, setError] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloadName, setDownloadName] = useState("");

  // Avoid state update after unmount + allow cancel
  const abortRef = useRef(null);

  const payload = useMemo(() => {
    try {
      const cfg = JSON.parse(localStorage.getItem("pcl_config") || "{}");
      const pole = JSON.parse(localStorage.getItem("pcl_columns_pole") || "[]");
      const x = JSON.parse(localStorage.getItem("pcl_columns_x") || "[]");
      const y = JSON.parse(localStorage.getItem("pcl_columns_y") || "[]");
      const z = JSON.parse(localStorage.getItem("pcl_columns_z") || "[]");

      return {
        tracker_type: (cfg.trackerType || "flat").toLowerCase(), // MUST be "flat" or "xtr"
        pole,
        x,
        y,
        z,
      };
    } catch {
      return null;
    }
  }, []);

  async function generate() {
    setError("");
    setStatus("generating");

    // cleanup old download url
    if (downloadUrl) {
      URL.revokeObjectURL(downloadUrl);
      setDownloadUrl("");
    }
    setDownloadName("");

    if (!payload || !payload.pole?.length) {
      setError("Missing copied columns/config. Go back and copy columns first.");
      setStatus("error");
      return;
    }

    // cancel any previous request
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    try {
      // ✅ Use 127.0.0.1 to match your backend docs host (and avoid hostname mismatch issues)
      const res = await fetch("http://127.0.0.1:8000/api/fill-grading-tool", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        const text = await res.text();
        setError(`Backend error (${res.status}): ${text}`);
        setStatus("error");
        return;
      }

      const blob = await res.blob();

      const cd = res.headers.get("content-disposition") || "";
      const match = cd.match(/filename="([^"]+)"/i);
      const filename = match?.[1] || "GradingTool_Filled.xlsm";

      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
      setDownloadName(filename);
      setStatus("ready");
    } catch (e) {
      // Show a more useful message than "could not reach"
      const msg =
        e?.name === "AbortError"
          ? "Request cancelled."
          : `Network error reaching backend. Confirm backend is running and accessible at http://127.0.0.1:8000.
Try opening http://127.0.0.1:8000/docs in your browser.
Also ensure CORS allows http://localhost:5173 and http://127.0.0.1:5173.`;

      setError(msg);
      setStatus("error");
    }
  }

  useEffect(() => {
  return () => {
    if (abortRef.current) abortRef.current.abort();
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  };
}, [downloadUrl]);

  return (
    <div className="gt-shell">
      <div className="gt-topbar">
        <div>
          <h1 className="gt-title">Generate Grading Tool</h1>
          <p className="gt-subtitle">
            We will fill the selected grading tool template’s <b>Inputs</b> sheet automatically:
            <br />
            Points = 1..N, X→Easting, Y→Northing, Z→Elevation, Pole→Description.
          </p>
        </div>

        <div className="gt-actions">
          <Link to="/review" className="gt-link">
            ← Back to Review
          </Link>
        </div>
      </div>

      <div className="gt-panel">
        {status === "generating" && (
          <div className="gt-info">Generating filled .xlsm via Python backend…</div>
        )}

        {status === "error" && (
          <div className="gt-error">
            {error}
            <div style={{ marginTop: 10 }}>
              <button className="gt-secondary" onClick={generate}>
                Try again
              </button>
            </div>
          </div>
        )}

        {status === "ready" && (
          <div className="gt-ready">
            <div className="gt-success">Done. Your filled grading tool is ready.</div>

            <a className="gt-download" href={downloadUrl} download={downloadName}>
              Download updated Excel (.xlsm)
            </a>

            <button className="gt-secondary" onClick={generate}>
              Regenerate
            </button>
          </div>
        )}

        {status === "idle" && (
          <button className="gt-primary" onClick={generate}>
            Generate now
          </button>
        )}
      </div>
    </div>
  );
}
