import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Uploads.css";

export default function Uploads() {
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
    <div className="uploads-page">
      <header className="uploads-topbar">
        <div className="topbar-left">
          <Link to="/" className="back-link">
            ← Back
          </Link>
          <div className="topbar-titlewrap">
            <h1 className="topbar-title">Upload BOM</h1>
            <p className="topbar-subtitle">
              Upload your BOM Excel file (.xlsx). You’ll review it on the next page.
            </p>
          </div>
        </div>
        <div className="topbar-badge">Step 1 of 3</div>
      </header>

      <main className="uploads-content">
        <section className="card">
          <div className="card-header">
            <h2 className="card-title">BOM File</h2>
            <p className="card-subtitle">Accepted format: .xlsx</p>
          </div>

          <div
            className={`dropzone ${isDragging ? "is-dragging" : ""}`}
            onClick={onBrowseClick}
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            onDragEnter={() => setIsDragging(true)}
            onDragLeave={() => setIsDragging(false)}
            role="button"
            tabIndex={0}
          >
            <div className="dropzone-icon" aria-hidden="true">
              ⬆
            </div>
            <div className="dropzone-text">
              <div className="dropzone-title">Drag & drop your BOM here</div>
              <div className="dropzone-subtitle">or click to browse files</div>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              className="hidden-input"
              onChange={(e) => validateAndSetFile(e.target.files?.[0])}
            />
          </div>

          {error && <div className="alert alert-error">{error}</div>}
          {statusMsg && <div className="alert alert-success">{statusMsg}</div>}

          {bomFile && (
            <div className="filecard">
              <div className="filecard-left">
                <div className="filechip">XLSX</div>
                <div className="filemeta">
                  <div className="filename">{bomFile.name}</div>
                  <div className="filesub">
                    {(bomFile.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>
              </div>

              <button className="btn btn-ghost" onClick={clearFile}>
                Remove
              </button>
            </div>
          )}

          <div className="card-actions">
            <button
              className={`btn btn-primary ${canContinue ? "" : "is-disabled"}`}
              onClick={continueToReview}
              disabled={!canContinue}
            >
              Continue →
            </button>
          </div>

          <div className="helper">
            <div className="helper-title">Tip</div>
            <div className="helper-text">
              If your file is large, the next page may take a few seconds to load and render.
            </div>
          </div>
        </section>
      </main>

      <footer className="uploads-footer">
        <span className="footer-muted">
          PCL Earthworks Tool • Upload → Review → Parameters
        </span>
      </footer>
    </div>
  );
}
