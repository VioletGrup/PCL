import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Uploads.css";

import pclLogo from "../assets/logos/pcllogo.png";
import backgroundImage from "../assets/logos/Australia-Office-2025.png";

export default function Uploads() {
  /**
   * Purpose: BOM upload page styled with premium PCL theme (dark/light via [data-theme]).
   * Name: Uploads.jsx
   * Date created: 2026-01-20
   * Method: Drag/drop + browse file input with validation; persists selection via navigation state.
   * Data dictionary:
   *  - bomFile (File|null): selected Excel file (.xlsx).
   *  - error (string): validation error message.
   *  - statusMsg (string): success/ready status message.
   *  - isDragging (boolean): drag-over UI state.
   */

  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const [bomFile, setBomFile] = useState(null);
  const [error, setError] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  // ✅ animated center toast
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

  function validateAndSetFile(file) {
    setError("");
    setStatusMsg("");

    if (!file) return;

    const name = file.name.toLowerCase();
    const isXlsx = name.endsWith(".xlsx");

    if (!isXlsx) {
      setBomFile(null);
      const msg = "Please upload a valid .xlsx Excel file (BOM).";
      setError(msg);
      showToast(msg, "error", 1700);
      return;
    }

    setBomFile(file);
    showToast("File uploaded successfully", "success", 1400);
    setStatusMsg("File ready. Click Continue to review.");
  }

  function onDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    validateAndSetFile(e.dataTransfer.files?.[0]);
  }

  function onBrowseClick() {
    setError("");
    setStatusMsg("");
    fileInputRef.current?.click();
  }

  function clearFile() {
    setBomFile(null);
    setError("");
    setStatusMsg("");
    if (fileInputRef.current) fileInputRef.current.value = "";
    showToast("File removed.", "info", 1200);
  }

  function continueToReview() {
    setError("");
    setStatusMsg("");

    if (!bomFile) {
      const msg = "Please upload your BOM .xlsx file to continue.";
      setError(msg);
      showToast(msg, "error", 1700);
      return;
    }

    showToast("Opening Review…", "info", 850);

    navigate("/review", {
      state: {
        bomFile,
        fileName: bomFile.name,
        fileSize: bomFile.size,
        uploadedAt: new Date().toISOString(),
      },
    });
  }

  function goToCustomUploads() {
    showToast("Opening Custom Uploads…", "info", 700);
    navigate("/customuploads");
  }

  const canContinue = !!bomFile;

  return (
    <div className="upl-shell">
      {toast.open && (
        <div className={`upl-toastOverlay ${toast.visible ? "is-visible" : ""}`}>
          <div
            className={[
              "upl-toastCard",
              toast.variant === "success" ? "is-success" : "",
              toast.variant === "error" ? "is-error" : "",
              toast.visible ? "is-visible" : "",
            ].join(" ")}
            role="status"
            aria-live="polite"
          >
            <div className="upl-toastIcon" aria-hidden="true">
              {toast.variant === "success" ? "✓" : toast.variant === "error" ? "!" : "i"}
            </div>
            <div className="upl-toastText">{toast.message}</div>
          </div>
        </div>
      )}

      <div className="upl-bg" aria-hidden="true">
        <img src={backgroundImage} alt="" className="upl-bgImg" />
        <div className="upl-bgOverlay" />
        <div className="upl-gridOverlay" />
      </div>

      <header className="upl-header">
        <div className="upl-headerInner">
          <div className="upl-brand">
            <img src={pclLogo} alt="PCL Logo" className="upl-logo" />
            <div className="upl-brandText">
              <div className="upl-brandTitle">Earthworks Analysis Tool</div>
              <div className="upl-brandSub">Upload → Review → Parameters</div>
            </div>
          </div>

          <div className="upl-nav">
            <Link to="/" className="upl-navLink">
              ← Back
            </Link>

            <div className="upl-stepPill">
              <span className="upl-stepDot" />
              Step 1 of 3
            </div>
          </div>
        </div>
      </header>

      <main className="upl-main">
        <div className="upl-pageTitle">
          <div className="upl-badge">
            <span className="upl-badgeDot" />
            Upload BOM
          </div>

          <h1 className="upl-h1">BOM Upload</h1>

          <p className="upl-subtitle">
            Upload your <span className="upl-em">BOM Excel file (.xlsx)</span>. You’ll review it
            on the next page before continuing.
          </p>
        </div>

        <div className="upl-stepper" aria-label="Progress steps">
          <div className="upl-step is-active">
            <div className="upl-stepCircle">1</div>
            <div className="upl-stepText">
              <div className="upl-stepTitle">Upload</div>
              <div className="upl-stepSub">Select .xlsx</div>
            </div>
          </div>

          <div className="upl-stepLine" />

          <div className="upl-step">
            <div className="upl-stepCircle">2</div>
            <div className="upl-stepText">
              <div className="upl-stepTitle">Review</div>
              <div className="upl-stepSub">Check inputs</div>
            </div>
          </div>

          <div className="upl-stepLine" />

          <div className="upl-step">
            <div className="upl-stepCircle">3</div>
            <div className="upl-stepText">
              <div className="upl-stepTitle">Parameters</div>
              <div className="upl-stepSub">Run analysis</div>
            </div>
          </div>
        </div>

        <section className="upl-card">
          <div className="upl-cardHead">
            <div>
              <h2 className="upl-cardTitle">BOM File</h2>
              <p className="upl-cardSub">Accepted format: .xlsx</p>
            </div>

            <div className={bomFile ? "upl-chipOk" : "upl-chipIdle"}>
              {bomFile ? "File Ready" : "Waiting"}
            </div>
          </div>

          <div
            className={`upl-dropzone ${isDragging ? "is-dragging" : ""}`}
            onClick={onBrowseClick}
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            onDragEnter={() => setIsDragging(true)}
            onDragLeave={() => setIsDragging(false)}
            role="button"
            tabIndex={0}
          >
            <div className="upl-dropIcon" aria-hidden="true">
              ⬆
            </div>

            <div>
              <div className="upl-dropTitle">Drag & drop your BOM here</div>
              <div className="upl-dropSub">or click to browse files</div>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              className="upl-hiddenInput"
              onChange={(e) => validateAndSetFile(e.target.files?.[0])}
            />
          </div>

          {error && <div className="upl-alert upl-alertError">{error}</div>}
          {statusMsg && <div className="upl-alert upl-alertOk">{statusMsg}</div>}

          {bomFile && (
            <div className="upl-fileCard">
              <div className="upl-fileLeft">
                <div className="upl-fileChip">XLSX</div>

                <div className="upl-fileMeta">
                  <div className="upl-fileName">{bomFile.name}</div>
                  <div className="upl-fileSub">{(bomFile.size / 1024 / 1024).toFixed(2)} MB</div>
                </div>
              </div>

              <button className="upl-btn upl-btnGhost" onClick={clearFile}>
                Remove
              </button>
            </div>
          )}

          {/* ✅ NEW: Custom uploads button row */}
          <div className="upl-actions">
            <button className="upl-btn upl-btnGhost" onClick={goToCustomUploads}>
              Custom Uploads →
            </button>

            <button
              className={`upl-btn upl-btnPrimary ${canContinue ? "" : "is-disabled"}`}
              onClick={continueToReview}
              disabled={!canContinue}
            >
              Continue →
            </button>
          </div>

          <div className="upl-helper">
            <div className="upl-helperTitle">Tip</div>
            <div className="upl-helperText">
              Use <strong>Custom Uploads</strong> if your sheet headers don’t match the standard PCL
              template — you’ll map Frame/Pile/X/Y/Z first.
            </div>
          </div>
        </section>
      </main>

      <footer className="upl-footer">
        <span className="upl-footerMuted">PCL Earthworks Tool • Upload → Review → Parameters</span>
      </footer>
    </div>
  );
}
