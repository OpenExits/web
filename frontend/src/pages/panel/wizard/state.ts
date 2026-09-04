// Wizard payload — mirrors the backend normalizer contract, plus draft
// persistence to localStorage so an interrupted phone session survives.
import type { SiteDocument } from "../../../lib/api";

export interface WizardFeature {
  role: "exit" | "landing" | "parking" | "gearup" | "trailhead";
  name?: string;
  lat: number;
  lon: number;
  elevationM?: number;
  positionSource: "gps" | "map";
  precisionM?: number;
  objectType?: string;
  suitability?: Record<string, boolean>;
  exitDirectionDeg?: number;
  approachTimeMin?: number;
  surface?: string;
  measurements?: Record<string, { valueM?: number; value?: number; reference?: string; method: string; measuredAt: string }>;
}

export interface WizardPayload {
  kind: "new_site" | "new_feature" | "correction";
  targetSitePath?: string;
  site: {
    name?: string;
    country?: string;
    status?: string;
    access?: string;
    region?: string;
    city?: string;
  };
  features: WizardFeature[];
  notes?: { language: string; observations?: string; hazards?: string };
  duplicateOverride?: boolean;
}

export function emptyPayload(): WizardPayload {
  return { kind: "new_site", site: {}, features: [] };
}

export function payloadFromSite(doc: SiteDocument, path: string): WizardPayload {
  return {
    kind: "correction",
    targetSitePath: path,
    site: {
      name: doc.name,
      country: doc.country,
      status: doc.status,
      access: doc.access,
      region: doc.region,
      city: doc.city,
    },
    features: doc.features.map((f) => ({
      role: f.role,
      name: f.name,
      lat: f.position.lat,
      lon: f.position.lon,
      elevationM: f.position.elevationM,
      positionSource: "map",
      precisionM: f.position.precisionM,
      objectType: f.objectType,
      suitability: f.suitability,
      exitDirectionDeg: f.exitDirectionDeg,
      approachTimeMin: f.approachTimeMin,
      surface: f.surface,
      measurements: f.measurements as WizardFeature["measurements"],
    })),
  };
}

const DRAFT_KEY = "openexits.wizard.draft";

export function loadDraft(): WizardPayload | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? (JSON.parse(raw) as WizardPayload) : null;
  } catch {
    return null;
  }
}

export function saveDraft(payload: WizardPayload): void {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(payload));
  } catch {
    /* storage unavailable */
  }
}

export function clearDraft(): void {
  try {
    localStorage.removeItem(DRAFT_KEY);
  } catch {
    /* storage unavailable */
  }
}
