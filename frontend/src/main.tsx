import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";

import "./i18n";
import "./styles.css";
import Layout from "./components/Layout";
import Docs from "./pages/Docs";
import Home from "./pages/Home";
import Placeholder from "./pages/Placeholder";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="docs" element={<Docs />} />
          <Route path="docs/:slug" element={<Docs />} />
          <Route path="map" element={<Placeholder title="Map" />} />
          <Route path="panel" element={<Placeholder title="Panel" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
