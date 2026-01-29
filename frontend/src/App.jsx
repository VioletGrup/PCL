// App.jsx
import React, { useEffect, useMemo, useState } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";

import pclLogo from "./assets/logos/pcllogo.png";
import backgroundImage from "./assets/logos/Australia-Office-2025.png";

import Uploads from "./pages/Uploads";
import Review from "./pages/Review";
import GradingTool from "./pages/GradingTool";
import Parameters from "./pages/Parameters";
import RunAnalysis from "./pages/RunAnalysis";
import FramePage from "./pages/FramePage";
import PileView from "./pages/PileView";
import CustomUploads from "./pages/CustomUploads"

export default function App() {
  /**
   * Purpose: Root router + premium landing page with working PCL-themed dark/light toggle across ALL pages.
   * Name: App.jsx
   * Date created: 2026-01-20
   * Method: Theme stored in localStorage; initial theme from storage or system preference; sets data-theme on <html> and <body>.
   * Data dictionary:
   *  - theme (string): "dark" | "light"
   *  - setTheme (function): state setter
   */

  const initialTheme = useMemo(() => {
    
  }, []);

  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    // Apply theme globally so every page picks it up
    document.documentElement.setAttribute("data-theme", theme);
    document.body.setAttribute("data-theme", theme);

    // Persist
    localStorage.setItem("pcl_theme", theme);

    // Optional: helps some browser UI
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  const toggleTheme = (e) => {
    e.preventDefault();
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  return (
    <BrowserRouter>
      <Routes>
        {/* LANDING */}
        <Route
          path="/"
          element={
            <div className="app-container">
              {/* Background */}
              <div className="background-wrapper" aria-hidden="true">
                <img src={backgroundImage} alt="" className="background-image" />
                <div className="background-overlay" />
                <div className="grid-overlay" />
              </div>

              {/* Header */}
              <header className="top-header">
                <div className="header-content">
                  <div className="brand">
                    <img src={pclLogo} alt="PCL Logo" className="header-logo" />
                    <div className="brand-text">
                      <div className="brand-title">Earthworks Analysis Tool</div>
                    </div>
                  </div>

                  <nav className="header-nav">
                    <button className="theme-toggle-nav" onClick={toggleTheme}>
                      {theme === "dark" ? (
                        <>
                          {/* moon icon */}
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                          >
                            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                          </svg>
                          Light Mode
                        </>
                      ) : (
                        <>
                          {/* sun icon */}
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                          >
                            <circle cx="12" cy="12" r="5" />
                            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                          </svg>
                          Dark Mode
                        </>
                      )}
                    </button>
                  </nav>
                </div>
              </header>

              {/* Main */}
              <main className="main-content">
                <section className="hero-section">
                  <div className="badge">
                    <span className="badge-dot" />
                    Advanced Analysis Platform
                  </div>

                  <h1 className="hero-title">PCL Earthworks Tool</h1>

                  <p className="hero-subtitle">
                    Professional-grade earthworks planning and optimization for solar
                    construction projects. Upload survey data, run grading calculations,
                    and generate outputs fast.
                  </p>

                  <div className="cta-group">
                    <Link to="/uploads" className="no-underline">
                      <button className="primary-button">
                        Get Started
                        <svg
                          width="20"
                          height="20"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M5 12h14M12 5l7 7-7 7" />
                        </svg>
                      </button>
                    </Link>

                    <button
                      className="secondary-button"
                      onClick={() => alert("User Manual coming soon")}
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <polygon points="5 3 19 12 5 21 5 3" />
                      </svg>
                      User Manual
                    </button>
                  </div>
                </section>

                <section className="features">
                  <div className="feature-item">
                    <div className="feature-icon">
                      <svg
                        width="32"
                        height="32"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                        <line x1="12" y1="22.08" x2="12" y2="12" />
                      </svg>
                    </div>
                    <div className="feature-number">01</div>
                    <h3>Upload & Validate</h3>
                    <p>
                      Import tracker templates and survey datasets with structured checks
                      before processing.
                    </p>
                  </div>

                  <div className="feature-item">
                    <div className="feature-icon">
                      <svg
                        width="32"
                        height="32"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
                        <path d="M22 12A10 10 0 0 0 12 2v10z" />
                      </svg>
                    </div>
                    <div className="feature-number">02</div>
                    <h3>Grading Analysis</h3>
                    <p>
                      Compute and optimise pile elevations, cut/fill requirements, and
                      grading outputs with chosen constraints.
                    </p>
                  </div>

                  <div className="feature-item">
                    <div className="feature-icon">
                      <svg
                        width="32"
                        height="32"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                      </svg>
                    </div>
                    <div className="feature-number">03</div>
                    <h3>Results & Visuals</h3>
                    <p>
                      Review and generate comprehensive reports with visualizations, and
                      export as CSV.
                    </p>
                  </div>
                </section>
              </main>

              <footer className="footer">
                <div className="footer-content">
                  <p>{new Date().getFullYear()} PCL Construction x UNSW</p>
                  <div className="footer-links">
                    <a href="#support" onClick={(e) => e.preventDefault()}>
                      Built by UNSW Engineering
                    </a>
                  </div>
                </div>
              </footer>
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
        <Route path="/pile/:pileId" element={<PileView />} />
        <Route path="/customuploads" element={<CustomUploads />} />

      
      </Routes>
    </BrowserRouter>
  );
}
