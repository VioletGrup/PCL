// Review.jsx
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import * as XLSX from "xlsx";
import "./Review.css";

export default function Review() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const [fileName, setFileName] = useState("");
  const [sheetName, setSheetName] = useState("");
  const [trackerType, setTrackerType] = useState("flat"); // "flat" | "xtr"

  // ✅ NOW: Frame + Pole + X + Y + Z(terrain enter)
  const [frame, setFrame] = useState([]);
  const [pole, setPole] = useState([]);
  const [x, setX] = useState([]);
  const [y, setY] = useState([]);
  const [z, setZ] = useState([]);

  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  // ✅ Manual mapping letters (editable)
  // Defaults match your screenshot: Table(A), Pole(C), X(D), Y(E), Z terrain enter(I)
  const [frameCol, setFrameCol] = useState("A");
  const [poleCol, setPoleCol] = useState("C");
  const [xCol, setXCol] = useState("D");
  const [yCol, setYCol] = useState("E");
  const [zCol, setZCol] = useState("I"); // ✅ Z terrain enter

  const [isApplying, setIsApplying] = useState(false);

  // ---------- helpers ----------
  const norm = (v) =>
    String(v ?? "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ");

  const sanitizeLetters = (s) =>
    String(s || "")
      .toUpperCase()
      .replace(/[^A-Z]/g, "")
      .slice(0, 3); // allows A..ZZZ (more than enough)

  const letterToColIndex = (letters) => {
    const s = String(letters || "").toUpperCase().trim();
    if (!s) return null;
    let n = 0;
    for (let i = 0; i < s.length; i++) {
      const code = s.charCodeAt(i);
      if (code < 65 || code > 90) return null; // not A-Z
      n = n * 26 + (code - 64);
    }
    return n - 1; // A->0
  };

  const toNumberIfPossible = (v) => {
    if (typeof v === "number") return v;
    const s = String(v ?? "").trim();
    if (s === "") return "";
    const n = Number(s);
    return Number.isFinite(n) ? n : s;
  };

  const persistSafely = (key, value) => {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch {
      return false;
    }
  };

  // Read rows for Piling Information sheet
  async function readPilingRows(bomFile) {
    const buffer = await bomFile.arrayBuffer();
    const wb = XLSX.read(buffer, { type: "array" });

    const targetNameNorm = "piling information";
    const matchedSheetName =
      wb.SheetNames.find((name) => norm(name) === targetNameNorm) ||
      wb.SheetNames.find((name) => norm(name).includes(targetNameNorm));

    if (!matchedSheetName) {
      throw new Error('Could not find a sheet named "Piling Information".');
    }

    const ws = wb.Sheets[matchedSheetName];
    const rows = XLSX.utils.sheet_to_json(ws, {
      header: 1,
      raw: true,
      defval: "",
    });

    if (!rows || rows.length === 0) {
      throw new Error('"Piling Information" sheet is empty.');
    }

    return { matchedSheetName, rows };
  }

  /**
   * DEFAULT extractor (fast + reliable):
   * Uses header-name validation to find the start row.
   * Now checks: Table, Pole, X, Y, Z terrain enter (loosely).
   */
  async function extractColumnsDefault(bomFile, idx) {
    const { matchedSheetName, rows } = await readPilingRows(bomFile);

    let headerRowIndex = -1;

    for (let i = 0; i < rows.length; i++) {
      const r = rows[i] || [];

      const tableH = norm(r[idx.frame]);
      const poleH = norm(r[idx.pole]);
      const xH = norm(r[idx.x]);
      const yH = norm(r[idx.y]);
      const zH = norm(r[idx.z]);

      const tableOk = tableH === "table";
      const poleOk = poleH === "pole";
      const xOk = xH === "x";
      const yOk = yH === "y";
      const zOk =
        zH === "z terrain enter" ||
        zH === "z" ||
        zH.includes("terrain") ||
        (zH.includes("z") && zH.includes("enter"));

      if (tableOk && poleOk && xOk && yOk && zOk) {
        headerRowIndex = i;
        break;
      }
    }

    if (headerRowIndex === -1) {
      throw new Error(
        `Could not find header row using mapping Frame=${frameCol}, Pole=${poleCol}, X=${xCol}, Y=${yCol}, Z=${zCol}.`
      );
    }

    const startIndex = headerRowIndex + 1;
    persistSafely("pcl_data_start_index", String(startIndex)); // tiny, safe

    return extractColumnsNoHeaderFromRows(rows, idx, startIndex, matchedSheetName);
  }

  /**
   * Manual remap extractor:
   * NO header-name checks. Just reads chosen columns from the SAME sheet,
   * starting at known startIndex (saved from default extraction).
   */
  async function extractColumnsNoHeader(bomFile, idx, startIndex) {
    const { matchedSheetName, rows } = await readPilingRows(bomFile);
    return extractColumnsNoHeaderFromRows(rows, idx, startIndex, matchedSheetName);
  }

  function extractColumnsNoHeaderFromRows(rows, idx, startIndex, matchedSheetName) {
    const start = Number.isFinite(startIndex) ? startIndex : 0;

    const outFrame = [];
    const outPole = [];
    const outX = [];
    const outY = [];
    const outZ = [];

    let emptyStreak = 0;
    const EMPTY_STREAK_LIMIT = 25;

    for (let i = start; i < rows.length; i++) {
      const r = rows[i] || [];

      const fVal = r[idx.frame] ?? "";
      const pVal = r[idx.pole] ?? "";
      const xVal = r[idx.x] ?? "";
      const yVal = r[idx.y] ?? "";
      const zVal = r[idx.z] ?? "";

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

      outFrame.push(toNumberIfPossible(fVal)); // usually numeric
      outPole.push(toNumberIfPossible(pVal));  // must be numeric
      outX.push(xVal);
      outY.push(yVal);
      outZ.push(zVal);
    }

    if (!outPole.length) {
      throw new Error("No data found in the selected columns.");
    }

    return { matchedSheetName, outFrame, outPole, outX, outY, outZ };
  }

  // ---------- initial load ----------
  useEffect(() => {
    setError("");
    setStatus("");

    // restore mapping letters if saved
    try {
      const saved = JSON.parse(localStorage.getItem("pcl_mapping_letters") || "null");
      if (saved?.frame) setFrameCol(String(saved.frame).toUpperCase());
      if (saved?.pole) setPoleCol(String(saved.pole).toUpperCase());
      if (saved?.x) setXCol(String(saved.x).toUpperCase());
      if (saved?.y) setYCol(String(saved.y).toUpperCase());
      if (saved?.z) setZCol(String(saved.z).toUpperCase());
    } catch {
      // ignore
    }

    // prefer localStorage columns (instant)
    try {
      const frameLS = JSON.parse(localStorage.getItem("pcl_columns_frame") || "[]");
      const poleLS = JSON.parse(localStorage.getItem("pcl_columns_pole") || "[]");
      const xLS = JSON.parse(localStorage.getItem("pcl_columns_x") || "[]");
      const yLS = JSON.parse(localStorage.getItem("pcl_columns_y") || "[]");
      const zLS = JSON.parse(localStorage.getItem("pcl_columns_z") || "[]");
      const cfg = JSON.parse(localStorage.getItem("pcl_config") || "{}");

      setFileName(state?.fileName || cfg.fileName || "");
      setSheetName(cfg.sheetName || "Piling information");
      setTrackerType(cfg.trackerType || "flat");

      if (poleLS.length && xLS.length && yLS.length && zLS.length) {
        setFrame(frameLS); // may be empty on older runs; that's ok
        setPole(poleLS);
        setX(xLS);
        setY(yLS);
        setZ(zLS);
        return;
      }
    } catch {
      // ignore; we will try extracting from bomFile next
    }

    // if no localStorage columns yet, extract from bomFile in navigation state
    const bomFile = state?.bomFile || null;
    if (!bomFile) {
      setError("No BOM file found. Go back to Uploads and continue again.");
      return;
    }

    (async () => {
      try {
        setStatus("Loading sheet…");

        const idx = {
          frame: letterToColIndex(frameCol) ?? 0, // A
          pole: letterToColIndex(poleCol) ?? 2,  // C
          x: letterToColIndex(xCol) ?? 3,        // D
          y: letterToColIndex(yCol) ?? 4,        // E
          z: letterToColIndex(zCol) ?? 8,        // I
        };

        const { matchedSheetName, outFrame, outPole, outX, outY, outZ } =
          await extractColumnsDefault(bomFile, idx);

        setFileName(state?.fileName || bomFile.name || "");
        setSheetName(matchedSheetName);

        setFrame(outFrame);
        setPole(outPole);
        setX(outX);
        setY(outY);
        setZ(outZ);

        setStatus("");

        // cache for refresh-safe (best effort)
        const okF = persistSafely("pcl_columns_frame", JSON.stringify(outFrame));
        const ok1 = persistSafely("pcl_columns_pole", JSON.stringify(outPole));
        const ok2 = persistSafely("pcl_columns_x", JSON.stringify(outX));
        const ok3 = persistSafely("pcl_columns_y", JSON.stringify(outY));
        const ok4 = persistSafely("pcl_columns_z", JSON.stringify(outZ));

        persistSafely(
          "pcl_config",
          JSON.stringify({
            fileName: state?.fileName || bomFile.name,
            sheetName: matchedSheetName,
            trackerType: "flat",
          })
        );

        persistSafely(
          "pcl_mapping_letters",
          JSON.stringify({
            frame: frameCol,
            pole: poleCol,
            x: xCol,
            y: yCol,
            z: zCol,
          })
        );

        if (!(ok1 && ok2 && ok3 && ok4 && okF)) {
          setStatus("Loaded. Note: browser storage is full, so refresh may require re-upload.");
        }
      } catch (e) {
        setStatus("");
        setError(e?.message || "Failed to read BOM file.");
      }
    })();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  const rowCount = useMemo(() => {
    return Math.min(frame.length || Infinity, pole.length, x.length, y.length, z.length);
  }, [frame, pole, x, y, z]);

  const PREVIEW_N = 2000;
  const previewCount = Math.min(rowCount || 0, PREVIEW_N);

  function proceedToGradingTool() {
    setError("");
    if (!rowCount) {
      setError("No rows found. Go back to Uploads and upload your BOM.");
      return;
    }
    navigate("/proceed-grading");
  }

  function goToParameters() {
    setError("");
    if (!rowCount) {
      setError("No rows found. Go back to Uploads and upload your BOM.");
      return;
    }
    navigate("/parameters", {
      state: { fileName, sheetName, trackerType, rowCount },
    });
  }

  // ✅ Apply mapping WITHOUT header-name checks
  async function applyMapping() {
    setError("");
    setStatus("");
    setIsApplying(true);

    try {
      const f = letterToColIndex(frameCol);
      const p = letterToColIndex(poleCol);
      const xc = letterToColIndex(xCol);
      const yc = letterToColIndex(yCol);
      const zc = letterToColIndex(zCol);

      if ([f, p, xc, yc, zc].some((v) => v === null)) {
        setError("Invalid column letter. Use A-Z (or AA, AB...).");
        return;
      }

      const bomFile = state?.bomFile || null;
      if (!bomFile) {
        setError("Remap needs the uploaded file. Go back to Uploads and continue again.");
        return;
      }

      const startIndex = Number(localStorage.getItem("pcl_data_start_index")) || 0;

      setStatus("Applying mapping…");

      const { matchedSheetName, outFrame, outPole, outX, outY, outZ } =
        await extractColumnsNoHeader(
          bomFile,
          { frame: f, pole: p, x: xc, y: yc, z: zc },
          startIndex
        );

      setSheetName(matchedSheetName);

      setFrame(outFrame);
      setPole(outPole);
      setX(outX);
      setY(outY);
      setZ(outZ);

      // save mapping letters only (safe)
      persistSafely(
        "pcl_mapping_letters",
        JSON.stringify({
          frame: frameCol,
          pole: poleCol,
          x: xCol,
          y: yCol,
          z: zCol,
        })
      );

      // best-effort cache columns
      const okF = persistSafely("pcl_columns_frame", JSON.stringify(outFrame));
      const ok1 = persistSafely("pcl_columns_pole", JSON.stringify(outPole));
      const ok2 = persistSafely("pcl_columns_x", JSON.stringify(outX));
      const ok3 = persistSafely("pcl_columns_y", JSON.stringify(outY));
      const ok4 = persistSafely("pcl_columns_z", JSON.stringify(outZ));

      persistSafely(
        "pcl_config",
        JSON.stringify({
          fileName: fileName || bomFile.name,
          sheetName: matchedSheetName,
          trackerType,
        })
      );

      if (!(ok1 && ok2 && ok3 && ok4 && okF)) {
        setStatus("Applied. Note: browser storage is full, so refresh may require re-upload.");
      } else {
        setStatus("Applied.");
        setTimeout(() => setStatus(""), 1200);
      }
    } catch (e) {
      setStatus("");
      setError(e?.message || "Failed to apply mapping.");
    } finally {
      setIsApplying(false);
    }
  }

  const templateName =
    trackerType === "xtr" ? "XTR.xlsm" : "Flat Tracker Imperial.xlsm";

  return (
    <div className="review-shell">
      <div className="review-topbar">
        <div className="review-left">
          <h1 className="review-title">Copied Columns</h1>

          <div className="review-meta">
            <div className="review-filename">{fileName || "—"}</div>

            <div className="review-count">
              Sheet: <strong>{sheetName || "—"}</strong> · Rows copied:{" "}
              <strong>{rowCount || 0}</strong>
              {rowCount > PREVIEW_N ? ` (showing first ${PREVIEW_N})` : ""}
            </div>

            <div className="review-count">
              Tracker: <strong>{trackerType.toUpperCase()}</strong> · Template:{" "}
              <strong>{templateName}</strong>
            </div>

            <div className="review-count">
              Columns:{" "}
              <strong>
                Frame={frameCol}, Pole={poleCol}, X={xCol}, Y={yCol}, Z={zCol}
              </strong>
            </div>
          </div>
        </div>

        <div className="review-actions">
          <Link to="/uploads" className="review-link">
            ← Back
          </Link>

          <button className="review-btn" onClick={() => navigate("/uploads")}>
            Upload New
          </button>

          <button
            className="review-primary"
            onClick={goToParameters}
            disabled={!rowCount}
            title="Go to the next step to enter parameters"
          >
            Next: Parameters →
          </button>
        </div>
      </div>

      <div className="review-mappingbar">
        <div className="inst-title">Column assignments (change if needed)</div>

        <div className="review-maprow">
          <div className="review-mapfield">
            <label>Frame</label>
            <input
              className="review-mapinput"
              value={frameCol}
              onChange={(e) => setFrameCol(sanitizeLetters(e.target.value))}
              placeholder="A"
            />
          </div>

          <div className="review-mapfield">
            <label>Pole</label>
            <input
              className="review-mapinput"
              value={poleCol}
              onChange={(e) => setPoleCol(sanitizeLetters(e.target.value))}
              placeholder="C"
            />
          </div>

          <div className="review-mapfield">
            <label>X</label>
            <input
              className="review-mapinput"
              value={xCol}
              onChange={(e) => setXCol(sanitizeLetters(e.target.value))}
              placeholder="D"
            />
          </div>

          <div className="review-mapfield">
            <label>Y</label>
            <input
              className="review-mapinput"
              value={yCol}
              onChange={(e) => setYCol(sanitizeLetters(e.target.value))}
              placeholder="E"
            />
          </div>

          <div className="review-mapfield">
            <label>Z</label>
            <input
              className="review-mapinput"
              value={zCol}
              onChange={(e) => setZCol(sanitizeLetters(e.target.value))}
              placeholder="I"
            />
          </div>

          <button className="review-btn" onClick={applyMapping} disabled={isApplying}>
            {isApplying ? "Applying…" : "Apply"}
          </button>

          <div className="inst-list">
            Default: Frame=A, Pole=C, X=D, Y=E, Z=I (Z terrain enter). Manual Apply ignores headers and shows chosen columns.
          </div>
        </div>
      </div>

      {status && <div className="review-status">{status}</div>}
      {error && <div className="review-error">{error}</div>}

      <div className="review-window">
        {!rowCount ? (
          <div className="review-empty">No data to display.</div>
        ) : (
          <table className="review-table">
            <thead>
              <tr>
                <th>Frame ({frameCol})</th>
                <th>Pole ({poleCol})</th>
                <th>X ({xCol})</th>
                <th>Y ({yCol})</th>
                <th>Z ({zCol})</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: previewCount }).map((_, i) => (
                <tr key={i}>
                  <td>{String(frame[i] ?? "")}</td>
                  <td>{String(pole[i] ?? "")}</td>
                  <td>{String(x[i] ?? "")}</td>
                  <td>{String(y[i] ?? "")}</td>
                  <td>{String(z[i] ?? "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="review-footer">
        Next step: proceed to download the correct grading tool template and the auto-mapped Inputs CSV.
      </div>
    </div>
  );
}
