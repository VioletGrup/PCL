import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import * as XLSX from "xlsx";
import "./CustomUploads.css";

import pclLogo from "../assets/logos/pcllogo.png";
import backgroundImage from "../assets/logos/Australia-Office-2025.png";

export default function CustomUploads() {
  /**
   * Purpose: Custom upload flow (.xlsx single-sheet OR .csv) with column letter assignment + preview + apply.
   * Name: CustomUploads.jsx
   * Date created: 2026-01-29
   * Method:
   *  1) Choose column letters (Frame/Pile/X/Y/Z)
   *  2) Upload CSV or XLSX (must be 1 sheet)
   *  3) Apply → extract into arrays + preview
   *  4) Change letters and Apply again if needed
   *  5) Continue → build XLSX where columns are placed at the SAME letters chosen, then navigate to /review
   * Data dictionary:
   *  - srcFile (File|null): uploaded source file
   *  - fileKind ("xlsx"|"csv"|""): detected type
   *  - sourceSheetName (string): original sheet name or "CSV"
   *  - aoa (any[][]): raw rows as array-of-arrays
   *  - frameCol/poleCol/xCol/yCol/zCol (string): mapping letters
   *  - extracted (object|null): extracted arrays + rowCount
   *  - error/status/toast: UI feedback
   */

  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // Mapping letters (user sets first)
  const [frameCol, setFrameCol] = useState("A");
  const [poleCol, setPoleCol] = useState("C");
  const [xCol, setXCol] = useState("D");
  const [yCol, setYCol] = useState("E");
  const [zCol, setZCol] = useState("I");

  // File state
  const [srcFile, setSrcFile] = useState(null);
  const [fileKind, setFileKind] = useState(""); // "xlsx" | "csv"
  const [sourceSheetName, setSourceSheetName] = useState("");
  const [aoa, setAoa] = useState([]); // raw AOA

  // Extracted result
  const [extracted, setExtracted] = useState(null); // { outFrame,outPole,outX,outY,outZ,rowCount }

  const [error, setError] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isApplying, setIsApplying] = useState(false);

  // Toast (same style as your Uploads)
  const [toast, setToast] = useState({
    open: false,
    visible: false,
    message: "",
    variant: "info", // "info" | "success" | "error"
  });

  const TOAST_OUT_MS = 220;
  const TOAST_DEFAULT_MS = 1500;
  const timersRef = useRef({ in: null, out: null, hide: null });

  const clearToastTimers = () => {
    const t = timersRef.current;
    if (t.in) window.clearTimeout(t.in);
    if (t.hide) window.clearTimeout(t.hide);
    if (t.out) window.clearTimeout(t.out);
    timersRef.current = { in: null, out: null, hide: null };
  };

  const showToast = (message, variant = "info", ms = TOAST_DEFAULT_MS) => {
    clearToastTimers();
    setToast({ open: true, visible: false, message, variant });

    timersRef.current.in = window.setTimeout(() => {
      setToast((prev) => ({ ...prev, visible: true }));
    }, 10);

    timersRef.current.hide = window.setTimeout(() => {
      setToast((prev) => ({ ...prev, visible: false }));
      timersRef.current.out = window.setTimeout(() => {
        setToast({ open: false, visible: false, message: "", variant: "info" });
      }, TOAST_OUT_MS);
    }, Math.max(350, ms));
  };

  useEffect(() => {
    return () => clearToastTimers();
  }, []);

  // ---------- helpers ----------
  const sanitizeLetters = (s) =>
    String(s || "")
      .toUpperCase()
      .replace(/[^A-Z]/g, "")
      .slice(0, 3);

  const letterToColIndex = (letters) => {
    const s = String(letters || "").toUpperCase().trim();
    if (!s) return null;
    let n = 0;
    for (let i = 0; i < s.length; i++) {
      const code = s.charCodeAt(i);
      if (code < 65 || code > 90) return null;
      n = n * 26 + (code - 64);
    }
    return n - 1;
  };

  const toNumberIfPossible = (v) => {
    if (typeof v === "number") return v;
    const s = String(v ?? "").trim();
    if (s === "") return "";
    const n = Number(s);
    return Number.isFinite(n) ? n : s;
  };

  function validateFile(file) {
    const name = file?.name?.toLowerCase?.() || "";
    const isXlsx = name.endsWith(".xlsx");
    const isCsv = name.endsWith(".csv");
    if (!isXlsx && !isCsv) return "Please upload a valid .xlsx or .csv file.";
    return "";
  }

  async function parseXlsxToAoa(file) {
    const buffer = await file.arrayBuffer();
    const wb = XLSX.read(buffer, { type: "array" });

    if (!wb.SheetNames?.length) throw new Error("No sheets found in this file.");
    if (wb.SheetNames.length !== 1) {
      throw new Error("Custom uploads requires exactly 1 sheet in the .xlsx file.");
    }

    const sn = wb.SheetNames[0];
    const ws = wb.Sheets[sn];

    const rows = XLSX.utils.sheet_to_json(ws, {
      header: 1,
      raw: true,
      defval: "",
    });

    if (!rows || rows.length === 0) throw new Error("Sheet is empty.");
    return { sheetName: sn, rows };
  }

  async function parseCsvToAoa(file) {
    const text = await new Promise((resolve, reject) => {
      const fr = new FileReader();
      fr.onerror = () => reject(new Error("Failed to read CSV file."));
      fr.onload = () => resolve(String(fr.result || ""));
      fr.readAsText(file);
    });

    const wb = XLSX.read(text, { type: "string" });
    const sn = wb.SheetNames?.[0];
    if (!sn) throw new Error("CSV parse failed (no sheet produced).");
    const ws = wb.Sheets[sn];

    const rows = XLSX.utils.sheet_to_json(ws, {
      header: 1,
      raw: true,
      defval: "",
    });

    if (!rows || rows.length === 0) throw new Error("CSV is empty.");
    return { sheetName: "CSV", rows };
  }

  async function loadFile(file) {
    setError("");
    setStatusMsg("");
    setSrcFile(null);
    setFileKind("");
    setSourceSheetName("");
    setAoa([]);
    setExtracted(null);

    const vErr = validateFile(file);
    if (vErr) {
      setError(vErr);
      showToast(vErr, "error", 1700);
      return;
    }

    try {
      showToast("Reading file…", "info", 900);

      const lower = file.name.toLowerCase();
      const kind = lower.endsWith(".csv") ? "csv" : "xlsx";

      const parsed = kind === "csv" ? await parseCsvToAoa(file) : await parseXlsxToAoa(file);

      setSrcFile(file);
      setFileKind(kind);
      setSourceSheetName(parsed.sheetName);
      setAoa(parsed.rows);

      setStatusMsg("File loaded. Click Apply to extract using your column letters.");
      showToast("File loaded. Ready to apply mapping.", "success", 1400);
    } catch (e) {
      setError(e?.message || "Failed to load file.");
      showToast(e?.message || "Failed to load file.", "error", 1700);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) loadFile(f);
  }

  function onBrowseClick() {
    setError("");
    setStatusMsg("");
    fileInputRef.current?.click();
  }

  function clearFile() {
    setSrcFile(null);
    setFileKind("");
    setSourceSheetName("");
    setAoa([]);
    setExtracted(null);
    setError("");
    setStatusMsg("");
    if (fileInputRef.current) fileInputRef.current.value = "";
    showToast("File removed.", "info", 1200);
  }

  // Extract 5 columns from raw AOA using letters; assumes row 0 is header and data starts row 1
  async function applyMapping() {
    setError("");
    setStatusMsg("");
    setIsApplying(true);

    try {
      if (!srcFile || !aoa.length) {
        setError("Upload a file first.");
        return;
      }

      const f = letterToColIndex(frameCol);
      const p = letterToColIndex(poleCol);
      const xc = letterToColIndex(xCol);
      const yc = letterToColIndex(yCol);
      const zc = letterToColIndex(zCol);

      if ([f, p, xc, yc, zc].some((v) => v === null)) {
        setError("Invalid column letter. Use A-Z (or AA, AB...).");
        return;
      }

      showToast("Applying mapping…", "info", 900);

      const outFrame = [];
      const outPole = [];
      const outX = [];
      const outY = [];
      const outZ = [];

      // assumes first row is headers
      const start = 1;

      let emptyStreak = 0;
      const EMPTY_STREAK_LIMIT = 25;

      for (let i = start; i < aoa.length; i++) {
        const r = aoa[i] || [];
        const fVal = r[f] ?? "";
        const pVal = r[p] ?? "";
        const xVal = r[xc] ?? "";
        const yVal = r[yc] ?? "";
        const zVal = r[zc] ?? "";

        const allEmpty =
          String(fVal).trim() === "" &&
          String(pVal).trim() === "" &&
          String(xVal).trim() === "" &&
          String(yVal).trim() === "" &&
          String(zVal).trim() === "";

        if (allEmpty) {
          emptyStreak += 1;
          if (emptyStreak >= EMPTY_STREAK_LIMIT) break;
          continue;
        }
        emptyStreak = 0;

        outFrame.push(toNumberIfPossible(fVal));
        outPole.push(toNumberIfPossible(pVal));
        outX.push(xVal);
        outY.push(yVal);
        outZ.push(zVal);
      }

      if (!outPole.length) {
        throw new Error("No data found in the selected columns (after the header row).");
      }

      const rowCount = Math.min(outFrame.length, outPole.length, outX.length, outY.length, outZ.length);

      setExtracted({ outFrame, outPole, outX, outY, outZ, rowCount });

      setStatusMsg("Applied. Preview below. Adjust letters and Apply again if needed.");
      showToast("Applied.", "success", 1200);
    } catch (e) {
      setExtracted(null);
      setStatusMsg("");
      setError(e?.message || "Failed to apply mapping.");
      showToast(e?.message || "Failed to apply mapping.", "error", 1700);
    } finally {
      setIsApplying(false);
    }
  }

  const rowCount = extracted?.rowCount || 0;
  const PREVIEW_N = 200;
  const previewCount = Math.min(rowCount, PREVIEW_N);

  const canContinue = !!srcFile && !!rowCount;

  // ✅ KEY FIX: create workbook where extracted columns are written INTO THE SAME LETTERS the user chose.
  function buildStandardWorkbookAndGoReview() {
    setError("");
    setStatusMsg("");

    if (!canContinue) {
      const msg = "Upload a file and Apply mapping before continuing.";
      setError(msg);
      showToast(msg, "error", 1700);
      return;
    }

    try {
      showToast("Preparing Review…", "info", 900);

      const { outFrame, outPole, outX, outY, outZ } = extracted;

      const idxFrame = letterToColIndex(frameCol);
      const idxPole = letterToColIndex(poleCol);
      const idxX = letterToColIndex(xCol);
      const idxY = letterToColIndex(yCol);
      const idxZ = letterToColIndex(zCol);

      if ([idxFrame, idxPole, idxX, idxY, idxZ].some((v) => v === null)) {
        const msg = "Invalid column letter. Use A-Z (or AA, AB...).";
        setError(msg);
        showToast(msg, "error", 1700);
        return;
      }

      const width = Math.max(idxFrame, idxPole, idxX, idxY, idxZ) + 1;

      const aoaOut = [];

      // header row in mapped columns
      const header = Array(width).fill("");
      header[idxFrame] = "Table";
      header[idxPole] = "Pile";
      header[idxX] = "X";
      header[idxY] = "Y";
      header[idxZ] = "Z terrain enter";
      aoaOut.push(header);

      for (let i = 0; i < rowCount; i++) {
        const r = Array(width).fill("");
        r[idxFrame] = outFrame[i];
        r[idxPole] = outPole[i];
        r[idxX] = outX[i];
        r[idxY] = outY[i];
        r[idxZ] = outZ[i];
        aoaOut.push(r);
      }

      const wb = XLSX.utils.book_new();
      const ws = XLSX.utils.aoa_to_sheet(aoaOut);
      XLSX.utils.book_append_sheet(wb, ws, "Piling Information");

      const arrayBuf = XLSX.write(wb, { bookType: "xlsx", type: "array" });

      const baseName =
        (srcFile?.name || "custom").replace(/\.(xlsx|csv)$/i, "").trim() || "custom";
      const outFileName = `${baseName}_custom_mapped.xlsx`;

      const outFile = new File([arrayBuf], outFileName, {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });

      navigate("/review", {
        state: {
          bomFile: outFile,
          fileName: outFile.name,
          fileSize: outFile.size,
          uploadedAt: new Date().toISOString(),
          mappingLetters: { frameCol, poleCol, xCol, yCol, zCol },
          customUpload: true,
          originalFileName: srcFile?.name || "",
          originalKind: fileKind,
          originalSheetName: sourceSheetName,
        },
      });
    } catch (e) {
      setError(e?.message || "Failed to prepare review file.");
      showToast(e?.message || "Failed to prepare review file.", "error", 1700);
    }
  }

  const kindLabel = fileKind === "csv" ? "CSV" : fileKind === "xlsx" ? "XLSX" : "—";

  return (
    <div className="cu-shell">
      {/* Toast */}
      {toast.open && (
        <div className={`cu-toastOverlay ${toast.visible ? "is-visible" : ""}`}>
          <div
            className={[
              "cu-toastCard",
              toast.variant === "success" ? "is-success" : "",
              toast.variant === "error" ? "is-error" : "",
              toast.visible ? "is-visible" : "",
            ].join(" ")}
            role="status"
            aria-live="polite"
          >
            <div className="cu-toastIcon" aria-hidden="true">
              {toast.variant === "success" ? "✓" : toast.variant === "error" ? "!" : "i"}
            </div>
            <div className="cu-toastText">{toast.message}</div>
          </div>
        </div>
      )}

      {/* Background */}
      <div className="cu-bg" aria-hidden="true">
        <img src={backgroundImage} alt="" className="cu-bgImg" />
        <div className="cu-bgOverlay" />
        <div className="cu-gridOverlay" />
      </div>

      {/* Header */}
      <header className="cu-header">
        <div className="cu-headerInner">
          <div className="cu-brand">
            <img src={pclLogo} alt="PCL Logo" className="cu-logo" />
            <div className="cu-brandText">
              <div className="cu-brandTitle">Earthworks Analysis Tool</div>
              <div className="cu-brandSub">Custom Uploads → Review → Parameters</div>
            </div>
          </div>

          <div className="cu-nav">
            <Link to="/uploads" className="cu-navLink">
              ← Back
            </Link>

            <div className="cu-stepPill">
              <span className="cu-stepDot" />
              Custom Imports
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="cu-main">
        <div className="cu-pageTitle">
          <div className="cu-badge">
            <span className="cu-badgeDot" />
            Custom Uploads
          </div>

          <h1 className="cu-h1">Assign Columns → Upload → Apply</h1>

          <p className="cu-subtitle">
            Set your column letters first, upload <span className="cu-em">.xlsx (1 sheet)</span> or{" "}
            <span className="cu-em">.csv</span>, then click <span className="cu-em">Apply</span> to
            preview. When correct, continue to Review.
          </p>
        </div>

        <section className="cu-card">
          <div className="cu-cardHead">
            <div>
              <h2 className="cu-cardTitle">Column letters (set before upload)</h2>
              <p className="cu-cardSub">
                After upload, press <strong>Apply</strong>. You can edit letters and apply again.
              </p>
            </div>

            <div className={canContinue ? "cu-chipOk" : "cu-chipIdle"}>
              {canContinue ? "Ready" : "Waiting"}
            </div>
          </div>

          {/* Mapping row */}
          <div className="cu-mapRow">
            <div className="cu-field">
              <label className="cu-label">Frame</label>
              <input
                className="cu-input"
                value={frameCol}
                onChange={(e) => setFrameCol(sanitizeLetters(e.target.value))}
                placeholder="A"
              />
            </div>

            <div className="cu-field">
              <label className="cu-label">Pile</label>
              <input
                className="cu-input"
                value={poleCol}
                onChange={(e) => setPoleCol(sanitizeLetters(e.target.value))}
                placeholder="C"
              />
            </div>

            <div className="cu-field">
              <label className="cu-label">X</label>
              <input
                className="cu-input"
                value={xCol}
                onChange={(e) => setXCol(sanitizeLetters(e.target.value))}
                placeholder="D"
              />
            </div>

            <div className="cu-field">
              <label className="cu-label">Y</label>
              <input
                className="cu-input"
                value={yCol}
                onChange={(e) => setYCol(sanitizeLetters(e.target.value))}
                placeholder="E"
              />
            </div>

            <div className="cu-field">
              <label className="cu-label">Z</label>
              <input
                className="cu-input"
                value={zCol}
                onChange={(e) => setZCol(sanitizeLetters(e.target.value))}
                placeholder="I"
              />
            </div>

            <button className="cu-btn" onClick={applyMapping} disabled={!srcFile || isApplying}>
              {isApplying ? "Applying…" : "Apply"}
            </button>
          </div>

          {/* Dropzone */}
          <div
            className={`cu-dropzone ${isDragging ? "is-dragging" : ""}`}
            onClick={onBrowseClick}
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            onDragEnter={() => setIsDragging(true)}
            onDragLeave={() => setIsDragging(false)}
            role="button"
            tabIndex={0}
            style={{ marginTop: 14 }}
          >
            <div className="cu-dropIcon" aria-hidden="true">
              ⬆
            </div>

            <div>
              <div className="cu-dropTitle">Upload file</div>
              <div className="cu-dropSub">Click or drop here (.xlsx or .csv)</div>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.csv"
              className="cu-hiddenInput"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) loadFile(f);
              }}
            />
          </div>

          {statusMsg && <div className="cu-alert cu-alertOk">{statusMsg}</div>}
          {error && <div className="cu-alert cu-alertError">{error}</div>}

          {srcFile && (
            <div className="cu-fileCard">
              <div className="cu-fileLeft">
                <div className="cu-fileChip">{kindLabel}</div>

                <div className="cu-fileMeta">
                  <div className="cu-fileName">{srcFile.name}</div>
                  <div className="cu-fileSub">
                    Source: <strong>{sourceSheetName || "—"}</strong> ·{" "}
                    {(srcFile.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>
              </div>

              <button className="cu-btn cu-btnGhost" onClick={clearFile}>
                Remove
              </button>
            </div>
          )}

          {/* Preview */}
          {extracted && rowCount > 0 && (
            <>
              <div className="cu-previewTitle" style={{ marginTop: 16 }}>
                Preview (showing {previewCount} of {rowCount} rows)
              </div>

              <div className="cu-tableWrap">
                <table className="cu-table">
                  <thead>
                    <tr>
                      <th>Frame ({frameCol})</th>
                      <th>Pile ({poleCol})</th>
                      <th>X ({xCol})</th>
                      <th>Y ({yCol})</th>
                      <th>Z ({zCol})</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Array.from({ length: previewCount }).map((_, i) => (
                      <tr key={i}>
                        <td>{String(extracted.outFrame[i] ?? "")}</td>
                        <td>{String(extracted.outPole[i] ?? "")}</td>
                        <td>{String(extracted.outX[i] ?? "")}</td>
                        <td>{String(extracted.outY[i] ?? "")}</td>
                        <td>{String(extracted.outZ[i] ?? "")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="cu-footHint">
                If anything looks wrong, change the letters above and press <strong>Apply</strong>{" "}
                again.
              </div>
            </>
          )}

          {/* Actions */}
          <div className="cu-actions">
            <button className="cu-btn cu-btnGhost" onClick={() => navigate("/uploads")}>
              Back to Uploads
            </button>

            <button
              className={`cu-btn cu-btnPrimary ${canContinue ? "" : "is-disabled"}`}
              onClick={buildStandardWorkbookAndGoReview}
              disabled={!canContinue}
              title={!canContinue ? "Upload + Apply first" : "Continue to Review"}
            >
              Continue →
            </button>
          </div>
        </section>
      </main>

      <footer className="cu-footer">
        <span className="cu-footerMuted">
          PCL Earthworks Tool • Custom Uploads → Review → Parameters
        </span>
      </footer>
    </div>
  );
}
