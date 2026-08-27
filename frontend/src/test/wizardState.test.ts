import {
  clearDraft, emptyPayload, loadDraft, payloadFromSite, saveDraft,
} from "../pages/panel/wizard/state";
import type { SiteDocument } from "../lib/api";

describe("wizard state", () => {
  it("persists and restores a draft via localStorage", () => {
    clearDraft();
    expect(loadDraft()).toBeNull();
    const p = emptyPayload();
    p.site.name = "Falaise Brouillon";
    p.features.push({ role: "exit", lat: 45.7, lon: 6.3, positionSource: "gps" });
    saveDraft(p);
    const restored = loadDraft();
    expect(restored?.site.name).toBe("Falaise Brouillon");
    expect(restored?.features[0].lat).toBe(45.7);
    clearDraft();
    expect(loadDraft()).toBeNull();
  });

  it("maps a published site into a correction payload", () => {
    const doc = {
      schemaVersion: "2.0",
      id: "01J9X0AAAAAAAAAAAAAAAAAAAA",
      name: "Pointe du Héron",
      country: "FR",
      status: "open",
      access: "tolerated",
      sensitivity: "public",
      provenance: [{ source: "panel", contributor: "heron_n", contributedAt: "2026-04-02" }],
      updatedAt: "2026-08-27T09:00:00Z",
      features: [
        {
          role: "exit",
          position: { lat: 45.9012, lon: 6.5123, elevationM: 2140 },
          suitability: { sliderOff: true },
          exitDirectionDeg: 210,
        },
        { role: "landing", surface: "grass", position: { lat: 45.8951, lon: 6.5089 } },
      ],
    } as SiteDocument;
    const p = payloadFromSite(doc, "fr/pointe-du-heron");
    expect(p.kind).toBe("correction");
    expect(p.targetSitePath).toBe("fr/pointe-du-heron");
    expect(p.site.name).toBe("Pointe du Héron");
    expect(p.features).toHaveLength(2);
    expect(p.features[0].exitDirectionDeg).toBe(210);
    expect(p.features[1].role).toBe("landing");
  });
});
