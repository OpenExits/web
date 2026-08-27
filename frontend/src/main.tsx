import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";

import "./i18n";
import "./styles.css";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Placeholder from "./pages/Placeholder";

// Route-level code splitting: MapLibre and the markdown renderer stay out of
// the homepage bundle.
const MapPage = lazy(() => import("./pages/Map"));
const Docs = lazy(() => import("./pages/Docs"));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Suspense fallback={<div className="p-16 text-center text-muted">…</div>}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="docs" element={<Docs />} />
            <Route path="docs/:slug" element={<Docs />} />
            <Route path="map" element={<MapPage />} />
            <Route path="panel" element={<Placeholder title="Panel" />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  </StrictMode>,
);
