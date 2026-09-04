import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";

import "./i18n";
import "./styles.css";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import { PANEL_ENABLED } from "./lib/api";
import { AuthProvider } from "./lib/auth";
import PanelUnavailable from "./pages/PanelUnavailable";
import RequireAuth from "./pages/panel/RequireAuth";

// Route-level code splitting: MapLibre and the markdown renderer stay out of
// the homepage bundle.
const MapPage = lazy(() => import("./pages/Map"));
const Docs = lazy(() => import("./pages/Docs"));
const Terms = lazy(() => import("./pages/Terms"));
const PanelHome = lazy(() => import("./pages/panel/PanelHome"));
const Wizard = lazy(() => import("./pages/panel/wizard/Wizard"));
const Submissions = lazy(() => import("./pages/panel/Submissions"));
const Moderation = lazy(() => import("./pages/panel/Moderation"));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<div className="p-16 text-center text-muted">…</div>}>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="docs" element={<Docs />} />
              <Route path="docs/:slug" element={<Docs />} />
              <Route path="map" element={<MapPage />} />
              <Route path="terms" element={<Terms />} />
              {PANEL_ENABLED ? (
                <>
                  <Route path="panel" element={<PanelHome />} />
                  <Route
                    path="panel/wizard"
                    element={
                      <RequireAuth>
                        <Wizard />
                      </RequireAuth>
                    }
                  />
                  <Route
                    path="panel/submissions"
                    element={
                      <RequireAuth>
                        <Submissions />
                      </RequireAuth>
                    }
                  />
                  <Route
                    path="panel/moderation"
                    element={
                      <RequireAuth>
                        <Moderation />
                      </RequireAuth>
                    }
                  />
                </>
              ) : (
                // A build with no backend: every panel route says so, rather
                // than offering a sign-in that cannot succeed.
                <Route path="panel/*" element={<PanelUnavailable />} />
              )}
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
);
