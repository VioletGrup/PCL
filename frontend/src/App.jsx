import "./App.css";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";

import pclLogo from "./assets/logos/pcllogo.png";

import Uploads from "./pages/Uploads";
import Review from "./pages/Review";
import GradingTool from "./pages/GradingTool";
import Parameters from "./pages/Parameters";
import RunAnalysis from "./pages/RunAnalysis";
import FramePage from "./pages/FramePage";


export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* HOME */}
        <Route
          path="/"
          element={
            <div className="app-container">
              <img src={pclLogo} alt="PCL Logo" className="app-logo" />
              <h1>PCL Earthworks Tool</h1>

              <Link to="/uploads">
              <div className = "app-button">
                <button>Go to Uploads</button>
              </div>
              </Link>
            </div>
          }
        />

        {/* PAGES */}
        <Route path="/uploads" element={<Uploads />} />
        <Route path="/review" element={<Review />} />
        <Route path="/proceed-grading" element={<GradingTool />} />
        <Route path="/parameters" element={<Parameters />} />
        <Route path="/run-analysis" element={<RunAnalysis />} />
        <Route path="/frame/:frameId" element={<FramePage />} />
      
      </Routes>
    </BrowserRouter>
  );
}
