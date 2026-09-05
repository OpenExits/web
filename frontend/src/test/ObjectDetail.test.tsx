import { render, screen } from "@testing-library/react";
import { act } from "react";

import i18n from "../i18n";
import ObjectDetail from "../components/ObjectDetail";
import type { ObjectDocument } from "../lib/api";

// SYNTHETIC object — invented name, invented coordinates.
const OBJ: ObjectDocument = {
  schemaVersion: "2.0",
  id: "01J9X0AAAAAAAAAAAAAAAAAAAA",
  name: "Pointe du Héron",
  country: "FR",
  region: "Massif des Ardines",
  city: "Saint-Elphe",
  status: "open",
  access: "tolerated",
  sensitivity: "public",
  objectType: "earth",
  provenance: [{ source: "panel", contributor: "heron_n", contributedAt: "2026-04-02" }],
  updatedAt: "2026-08-27T09:00:00Z",
  features: [
    {
      role: "exit",
      name: "High exit",
      position: { lat: 45.9012, lon: 6.5123, elevationM: 2140, pinConfirmed: true },
      suitability: { slick: false, sliderOff: true, sliderUp: true, wingsuit: true, tracksuit: true, staticLine: false },
      exitDirectionDeg: 210,
      approachTimeMin: 90,
      measurements: {
        rockdrop: { valueM: 220, method: "laser", measuredAt: "2026-05" },
        heightAgl: { valueM: 940, reference: "landing", method: "gps", measuredAt: "2026-05" },
      },
    },
    {
      role: "landing",
      name: "Pré Rond",
      surface: "grass",
      position: { lat: 45.8951, lon: 6.5089, elevationM: 1180 },
    },
  ],
};

describe("ObjectDetail", () => {
  it("renders the object in English with measurements, dates and the safety notice", async () => {
    await act(async () => {
      await i18n.changeLanguage("en");
    });
    render(<ObjectDetail doc={OBJ} />);
    expect(screen.getByText("Pointe du Héron")).toBeInTheDocument();
    expect(screen.getByText("OPEN")).toBeInTheDocument();
    expect(screen.getByText("ACCESS: TOLERATED")).toBeInTheDocument();
    expect(screen.getByText("Rockdrop")).toBeInTheDocument();
    expect(screen.getByText(/laser · 2026-05/)).toBeInTheDocument(); // staleness visible (OE-R09)
    expect(screen.getByText("Height AGL (landing)")).toBeInTheDocument();
    expect(screen.getByText(/210° true/)).toBeInTheDocument();
    expect(screen.getByText(/unverified reference information/)).toBeInTheDocument();
    expect(screen.getByText("Pré Rond")).toBeInTheDocument();
    expect(screen.getByText("@heron_n")).toBeInTheDocument();
  });

  it("renders in French", async () => {
    await act(async () => {
      await i18n.changeLanguage("fr");
    });
    render(<ObjectDetail doc={OBJ} />);
    expect(screen.getByText("OUVERT")).toBeInTheDocument();
    expect(screen.getByText("ACCÈS : TOLÉRÉ")).toBeInTheDocument();
    expect(screen.getByText("Hauteur sol (landing)")).toBeInTheDocument();
    expect(screen.getByText(/information de référence non vérifiée/)).toBeInTheDocument();
  });

  it("strikes through unavailable suitability entries", async () => {
    await act(async () => {
      await i18n.changeLanguage("en");
    });
    render(<ObjectDetail doc={OBJ} />);
    expect(screen.getByText("slick").className).toContain("line-through");
    expect(screen.getByText("wingsuit").className).not.toContain("line-through");
  });
});
