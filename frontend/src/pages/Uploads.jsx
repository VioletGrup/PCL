import { useRef, useState } from "react";
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

  function validateAndSetFile(file) {
    setError("");
    setStatusMsg("");

    if (!file) return;

    const name = file.name.toLowerCase();
    const isXlsx = name.endsWith(".xlsx");

    if (!isXlsx) {
      setBomFile(null);
      setError("Please upload a valid .xlsx Excel file (BOM).");
      return;
    }

    setBomFile(file);
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
  }

  function continueToReview() {
    setError("");
    setStatusMsg("");

    if (!bomFile) {
      setError("Please upload your BOM .xlsx file to continue.");
      return;
    }

    navigate("/review", {
      state: {
        bomFile,
        fileName: bomFile.name,
        fileSize: bomFile.size,
        uploadedAt: new Date().toISOString(),
      },
    });
  }

  const canContinue = !!bomFile;

  return (
    <div className="upl-shell">
      {/* Background (matches App landing page) */}
      <div className="upl-bg" aria-hidden="true">
        <img src={backgroundImage} alt="" className="upl-bgImg" />
        <div className="upl-bgOverlay" />
        <div className="upl-gridOverlay" />
      </div>

      {/* Header */}
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

      {/* Main */}
      <main className="upl-main">
        {/* Title */}
        <div className="upl-pageTitle">
          <div className="upl-badge">
            <span className="upl-badgeDot" />
            Upload BOM
          </div>

          <h1 className="upl-h1">BOM Upload</h1>

          <p className="upl-subtitle">
            Upload your <span className="upl-em">BOM Excel file (.xlsx)</span>. You’ll
            review it on the next page before continuing.
          </p>
        </div>

        {/* Stepper */}
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

        {/* Card */}
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
                  <div className="upl-fileSub">
                    {(bomFile.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>
              </div>

              <button className="upl-btn upl-btnGhost" onClick={clearFile}>
                Remove
              </button>
            </div>
          )}

          <div className="upl-actions">
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
              If your file is large, the next page may take a few seconds to load and render.
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="upl-footer">
        <span className="upl-footerMuted">
          PCL Earthworks Tool • Upload → Review → Parameters
        </span>
      </footer>
    </div>
  );
}
