// Wizard payload — mirrors the backend normalizer contract, plus draft
// persistence to localStorage so an interrupted phone session survives.
import type { ObjectDocument } from "../../../lib/api";

export interface WizardFeature {
  role: "exit" | "landing" | "parking" | "gearup" | "trailhead";
  name?: string;
  lat: number;
  lon: number;
  elevationM?: number;
  positionSource: "gps" | "map";
  precisionM?: number;
  suitability?: Record<string, boolean>;
  exitDirectionDeg?: number;
  approachTimeMin?: number;
  surface?: string;
  measurements?: Record<string, { valueM?: number; value?: number; reference?: string; method: string; measuredAt: string }>;
}

export interface WizardPayload {
  kind: "new_object" | "new_feature" | "correction";
  targetObjectPath?: string;
  object: {
    name?: string;
    country?: string;
    objectType?: string;
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
  return { kind: "new_object", object: {}, features: [] };
}

export function payloadFromObject(doc: ObjectDocument, path: string): WizardPayload {
  return {
    kind: "correction",
    targetObjectPath: path,
    object: {
      name: doc.name,
      country: doc.country,
      objectType: doc.objectType,
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
      suitability: f.suitability,
      exitDirectionDeg: f.exitDirectionDeg,
      approachTimeMin: f.approachTimeMin,
      surface: f.surface,
      measurements: f.measurements as WizardFeature["measurements"],
    })),
  };
}

// v2: the payload shape changed (site -> object, objectType on the object);
// a new key discards drafts saved under the old shape instead of mis-reading them.
const DRAFT_KEY = "openexits.wizard.draft.v2";

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
