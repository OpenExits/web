import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router";
import { useTranslation } from "react-i18next";

import MapView from "../../../components/map/MapView";
import { useAuth } from "../../../lib/auth";
import { fetchObject } from "../../../lib/api";
import {
  clearDraft, emptyPayload, loadDraft, payloadFromObject, saveDraft,
  type WizardFeature, type WizardPayload,
} from "./state";

type Step = "notice" | "pin" | "details" | "measurements" | "landing" | "notes" | "review" | "done";
const STEP_ORDER: Step[] = ["notice", "pin", "details", "measurements", "landing", "notes", "review"];

interface NearbyHit {
  object_id: string;
  path: string | null;
  name: string;
  distance_m: number;
  feature_count: number;
  pending: boolean;
}

interface Finding {
  rule_id: string;
  level: string;
  path: string;
  message: string;
}

const inputCls =
  "rounded border border-line bg-white px-3.5 py-2.5 text-[15px] outline-none focus:border-ink";
const labelCls = "text-sm font-semibold";
const primaryBtn = "rounded bg-signal py-3.5 px-6 font-bold text-white disabled:opacity-50";
const secondaryBtn = "rounded border-[1.5px] border-line py-3.5 px-6 font-semibold text-muted";

const SUITABILITY_KEYS = ["slick", "sliderOff", "sliderUp", "wingsuit", "tracksuit", "staticLine"];
const OBJECT_TYPES = ["building", "antenna", "span", "earth"] as const;
const STATUSES = ["open", "closed", "destroyed", "seasonal", "unknown"];
const ACCESSES = ["legal", "tolerated", "restricted-seasonal", "illegal", "unknown"];

function exitOf(p: WizardPayload): WizardFeature | undefined {
  return p.features.find((f) => f.role === "exit");
}

function landingOf(p: WizardPayload): WizardFeature | undefined {
  return p.features.find((f) => f.role === "landing");
}

export default function Wizard() {
  const { t } = useTranslation(["wizard", "object"]);
  const { user, api, acceptTerms } = useAuth();
  const [params] = useSearchParams();
  const correctPath = params.get("correct");

  const [payload, setPayload] = useState<WizardPayload>(() => loadDraft() ?? emptyPayload());
  const [step, setStep] = useState<Step>(correctPath ? "details" : "notice");
  const [nearbyHits, setNearbyHits] = useState<NearbyHit[] | null>(null);
  const [termsChecked, setTermsChecked] = useState(user?.terms_accepted ?? false);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState<{ key: string; report?: Finding[] } | null>(null);
  const [result, setResult] = useState<{ publicId: string; flags: Record<string, unknown> } | null>(null);
  const [photoCount, setPhotoCount] = useState(0);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [gpsError, setGpsError] = useState(false);

  // correction prefill
  useEffect(() => {
    if (!correctPath) return;
    fetchObject(correctPath)
      .then((doc) => setPayload(payloadFromObject(doc, correctPath)))
      .catch(() => setSubmitError({ key: "wizard.target_not_found" }));
  }, [correctPath]);

  // draft autosave (not for corrections — those prefill from the live object)
  useEffect(() => {
    if (!correctPath && step !== "done") saveDraft(payload);
  }, [payload, correctPath, step]);

  const update = useCallback((fn: (p: WizardPayload) => WizardPayload) => {
    setPayload((p) => fn(structuredClone(p)));
  }, []);

  const setExit = useCallback(
    (patch: Partial<WizardFeature>) => {
      update((p) => {
        const idx = p.features.findIndex((f) => f.role === "exit");
        if (idx === -1) {
          p.features.unshift({ role: "exit", lat: 0, lon: 0, positionSource: "map", ...patch } as WizardFeature);
        } else {
          p.features[idx] = { ...p.features[idx], ...patch };
        }
        return p;
      });
    },
    [update],
  );

  const goNext = useCallback(() => {
    setStep((s) => STEP_ORDER[Math.min(STEP_ORDER.indexOf(s) + 1, STEP_ORDER.length - 1)]);
  }, []);
  const goBack = useCallback(() => {
    setStep((s) => STEP_ORDER[Math.max(STEP_ORDER.indexOf(s) - 1, 0)]);
  }, []);

  const checkNearby = useCallback(async () => {
    const exit = exitOf(payload);
    if (!exit || payload.kind !== "new_object") {
      goNext();
      return;
    }
    const r = await api(`/api/v1/objects/nearby?lat=${exit.lat}&lon=${exit.lon}`);
    const hits: NearbyHit[] = r.ok ? (await r.json()).hits : [];
    if (hits.length) setNearbyHits(hits);
    else goNext();
  }, [api, payload, goNext]);

  const attachToObject = useCallback(
    (hit: NearbyHit) => {
      update((p) => {
        p.kind = "new_feature";
        p.targetObjectPath = hit.path ?? undefined;
        p.object = {};
        return p;
      });
      setNearbyHits(null);
      goNext();
    },
    [update, goNext],
  );

  const submit = useCallback(async () => {
    setBusy(true);
    setSubmitError(null);
    if (!user?.terms_accepted) {
      const ok = await acceptTerms();
      if (!ok) {
        setBusy(false);
        setSubmitError({ key: "terms" });
        return;
      }
    }
    const r = await api("/api/v1/submissions", { method: "POST", body: JSON.stringify(payload) });
    const body = await r.json();
    setBusy(false);
    if (!r.ok) {
      setSubmitError({ key: body.error, report: body.report });
      return;
    }
    clearDraft();
    setResult({ publicId: body.submission.public_id, flags: body.machine_flags });
    setStep("done");
  }, [api, payload, user, acceptTerms]);

  const uploadPhoto = useCallback(
    async (file: File) => {
      if (!result) return;
      setPhotoError(null);
      const form = new FormData();
      form.append("file", file);
      const r = await api(`/api/v1/submissions/${result.publicId}/media`, {
        method: "POST",
        body: form,
      });
      if (r.ok) setPhotoCount((n) => n + 1);
      else setPhotoError((await r.json()).error ?? "media.failed");
    },
    [api, result],
  );

  const exit = exitOf(payload);
  const landing = landingOf(payload);
  const stepIdx = STEP_ORDER.indexOf(step === "done" ? "review" : step);

  const header = (
    <div className="flex flex-col gap-3 border-b border-line bg-granite px-5 py-4 text-paper">
      <div className="flex items-center justify-between">
        {step !== "notice" && step !== "done" ? (
          <button type="button" onClick={goBack} aria-label={t("wizard:back")} className="flex h-11 w-11 items-center justify-center">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M15 5 L8 12 L15 19" stroke="#f2f0ea" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        ) : (
          <span className="w-11" />
        )}
        <span className="text-[15px] font-bold">{t(`wizard:${step === "done" ? "result" : step}.title`)}</span>
        <span className="w-11 text-right font-mono text-xs text-ondark-muted">
          {stepIdx + 1}/{STEP_ORDER.length}
        </span>
      </div>
      <div className="flex gap-1">
        {STEP_ORDER.map((s, i) => (
          <span key={s} className={`h-[3px] flex-1 rounded ${i <= stepIdx ? "bg-signal" : "bg-[#3d4147]"}`} />
        ))}
      </div>
    </div>
  );

  const body = (() => {
    switch (step) {
      case "notice":
        return (
          <div className="flex flex-col gap-5 p-6">
            <div className="flex gap-3 rounded-md border border-warnline bg-warnbg p-4">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="shrink-0"><path d="M12 3 L22 20 H2 Z" stroke="#8a5a0a" strokeWidth="2" strokeLinejoin="round" /><path d="M12 10 V14.5" stroke="#8a5a0a" strokeWidth="2" strokeLinecap="round" /><circle cx="12" cy="17.2" r="1.2" fill="#8a5a0a" /></svg>
              <p className="text-sm leading-relaxed text-warntext">{t("wizard:notice.body")}</p>
            </div>
            <p className="text-sm text-muted">{t("wizard:notice.moderated")}</p>
            <button type="button" className={primaryBtn} onClick={goNext}>
              {t("wizard:notice.agree")}
            </button>
          </div>
        );

      case "pin":
        return (
          <div className="flex h-full flex-col">
            <div className="relative flex-1">
              <MapView
                onPick={(lat, lon) => setExit({ lat, lon, positionSource: "map", precisionM: 15 })}
                marker={exit && exit.lat !== 0 ? { lat: exit.lat, lon: exit.lon } : null}
              />
              <button
                type="button"
                onClick={() => {
                  setGpsError(false);
                  navigator.geolocation?.getCurrentPosition(
                    (pos) =>
                      setExit({
                        lat: Number(pos.coords.latitude.toFixed(6)),
                        lon: Number(pos.coords.longitude.toFixed(6)),
                        positionSource: "gps",
                        precisionM: Math.round(pos.coords.accuracy),
                        elevationM: pos.coords.altitude ? Math.round(pos.coords.altitude) : undefined,
                      }),
                    () => setGpsError(true),
                  );
                }}
                className="absolute right-3 top-3 rounded bg-white px-4 py-2.5 text-sm font-semibold shadow"
              >
                {t("wizard:pin.useGps")}
              </button>
            </div>
            <div className="flex flex-col gap-3 border-t border-line p-4">
              <p className="text-sm text-muted">{t("wizard:pin.hint")}</p>
              {gpsError && <p className="text-sm text-[#8f231d]">{t("wizard:pin.gpsFailed")}</p>}
              {exit && exit.lat !== 0 && (
                <p className="font-mono text-sm">
                  {exit.lat.toFixed(5)}, {exit.lon.toFixed(5)}
                  {exit.precisionM ? (
                    <span className="ml-2 text-xs text-faint">{t("wizard:pin.precision", { m: exit.precisionM })}</span>
                  ) : null}
                </p>
              )}
              <button type="button" className={primaryBtn} disabled={!exit || exit.lat === 0} onClick={checkNearby}>
                {t("wizard:pin.continue")}
              </button>
            </div>
            {nearbyHits && (
              <div className="absolute inset-x-0 bottom-0 z-10 flex flex-col gap-3.5 rounded-t-2xl bg-[#f7f5ef] p-5 shadow-[0_-6px_24px_rgba(0,0,0,0.25)]">
                <div className="text-base font-bold">{t("wizard:nearby.title")}</div>
                <p className="text-sm text-[#4a4c46]">{t("wizard:nearby.body")}</p>
                {nearbyHits.slice(0, 3).map((hit) => (
                  <button
                    key={hit.object_id}
                    type="button"
                    disabled={!hit.path}
                    onClick={() => attachToObject(hit)}
                    className="flex items-center justify-between rounded-lg border border-line bg-white px-4 py-3 text-left disabled:opacity-60"
                  >
                    <span className="flex flex-col">
                      <span className="text-[15px] font-bold">{hit.name}</span>
                      <span className="text-xs text-muted">
                        {t("wizard:nearby.features", { count: hit.feature_count })} ·{" "}
                        <span className="font-mono">{t("wizard:nearby.away", { m: hit.distance_m })}</span>
                        {hit.pending ? ` · ${t("wizard:nearby.pendingTag")}` : ""}
                      </span>
                    </span>
                  </button>
                ))}
                {nearbyHits[0].distance_m >= 50 ? (
                  <button
                    type="button"
                    className={secondaryBtn}
                    onClick={() => {
                      update((p) => ({ ...p, duplicateOverride: true }));
                      setNearbyHits(null);
                      goNext();
                    }}
                  >
                    {t("wizard:nearby.different")}
                  </button>
                ) : (
                  <p className="text-center text-xs text-faint">{t("wizard:nearby.tooClose", { m: 50 })}</p>
                )}
              </div>
            )}
          </div>
        );

      case "details": {
        const suit = exit?.suitability ?? {};
        return (
          <div className="flex flex-col gap-6 p-5">
            {payload.kind === "correction" && (
              <p className="rounded bg-[#e8edf5] px-3.5 py-2.5 text-sm text-[#33527d]">
                {t("wizard:correction.banner", { name: payload.object.name })}
              </p>
            )}
            {payload.kind !== "new_feature" && (
              <>
                <label className="flex flex-col gap-1.5">
                  <span className={labelCls}>{t("wizard:details.objectName")}</span>
                  <input
                    className={inputCls}
                    value={payload.object.name ?? ""}
                    onChange={(e) => update((p) => ({ ...p, object: { ...p.object, name: e.target.value } }))}
                  />
                  <span className="text-xs text-faint">{t("wizard:details.objectNameHint")}</span>
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className={labelCls}>{t("wizard:details.country")}</span>
                  <input
                    className={`${inputCls} w-28 font-mono uppercase`}
                    maxLength={2}
                    value={payload.object.country ?? ""}
                    onChange={(e) =>
                      update((p) => ({ ...p, object: { ...p.object, country: e.target.value.toUpperCase() } }))
                    }
                  />
                </label>
                <div className="flex gap-4">
                  <label className="flex flex-1 flex-col gap-1.5">
                    <span className={labelCls}>{t("wizard:details.status")}</span>
                    <select
                      className={inputCls}
                      value={payload.object.status ?? "open"}
                      onChange={(e) => update((p) => ({ ...p, object: { ...p.object, status: e.target.value } }))}
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>{t(`object:status.${s}`)}</option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-1 flex-col gap-1.5">
                    <span className={labelCls}>{t("wizard:details.access")}</span>
                    <select
                      className={inputCls}
                      value={payload.object.access ?? "unknown"}
                      onChange={(e) => update((p) => ({ ...p, object: { ...p.object, access: e.target.value } }))}
                    >
                      {ACCESSES.map((a) => (
                        <option key={a} value={a}>{t(`object:access.${a}`)}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="flex flex-col gap-2.5">
                  <span className={labelCls}>{t("wizard:details.objectType")}</span>
                  <div className="grid grid-cols-4 gap-2">
                    {OBJECT_TYPES.map((o) => (
                      <button
                        key={o}
                        type="button"
                        onClick={() => update((p) => ({ ...p, object: { ...p.object, objectType: o } }))}
                        className={
                          payload.object.objectType === o
                            ? "rounded-md bg-ink py-3.5 text-sm font-bold text-paper"
                            : "rounded-md border border-line bg-white py-3.5 text-sm font-semibold text-muted"
                        }
                      >
                        {t(`wizard:details.objects.${o}`)}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col gap-2.5">
                  <span className={labelCls}>{t("wizard:details.objectType")}</span>
                  <div className="grid grid-cols-4 gap-2">
                    {OBJECT_TYPES.map((o) => (
                      <button
                        key={o}
                        type="button"
                        onClick={() => update((p) => ({ ...p, object: { ...p.object, objectType: o } }))}
                        className={
                          payload.object.objectType === o
                            ? "rounded-md bg-ink py-3.5 text-sm font-bold text-paper"
                            : "rounded-md border border-line bg-white py-3.5 text-sm font-semibold text-muted"
                        }
                      >
                        {t(`wizard:details.objects.${o}`)}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
            <div className="flex flex-col gap-2.5">
              <div className="flex items-baseline justify-between">
                <span className={labelCls}>{t("wizard:details.suitability")}</span>
                <span className="text-xs text-faint">{t("wizard:details.suitabilityHint")}</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {SUITABILITY_KEYS.map((k) => (
                  <button
                    key={k}
                    type="button"
                    onClick={() => setExit({ suitability: { ...suit, [k]: !suit[k] } })}
                    className={
                      suit[k]
                        ? "flex h-12 items-center justify-between rounded-md border-[1.5px] border-signal bg-[#fdf1ea] px-3.5 text-sm font-bold"
                        : "flex h-12 items-center justify-between rounded-md border border-line bg-white px-3.5 text-sm font-semibold text-muted"
                    }
                  >
                    {t(`object:suitability.${k}`)}
                    <span className={suit[k] ? "text-signal" : "text-line"}>{suit[k] ? "✓" : "○"}</span>
                  </button>
                ))}
              </div>
            </div>
            <label className="flex flex-col gap-1.5">
              <span className={labelCls}>{t("wizard:details.direction")}</span>
              <input
                className={`${inputCls} w-32 font-mono`}
                type="number"
                min={0}
                max={359}
                value={exit?.exitDirectionDeg ?? ""}
                onChange={(e) =>
                  setExit({ exitDirectionDeg: e.target.value === "" ? undefined : Number(e.target.value) })
                }
              />
              <span className="text-xs text-faint">{t("wizard:details.directionHint")}</span>
            </label>
            <button
              type="button"
              className={primaryBtn}
              disabled={payload.kind !== "new_feature" && (!payload.object.name || !payload.object.country || (payload.kind === "new_object" && !payload.object.objectType) || !Object.values(suit).some(Boolean))}
              onClick={goNext}
            >
              {t("wizard:details.continue")}
            </button>
          </div>
        );
      }

      case "measurements": {
        const m = exit?.measurements ?? {};
        const setM = (key: string, patch: Record<string, unknown> | null) => {
          const next = { ...m } as Record<string, Record<string, unknown>>;
          if (patch === null) delete next[key];
          else next[key] = { ...(next[key] ?? { method: "estimate", measuredAt: "" }), ...patch };
          setExit({ measurements: next as WizardFeature["measurements"] });
        };
        const row = (key: "rockdrop" | "heightAgl") => {
          const entry = (m[key] ?? {}) as Record<string, unknown>;
          return (
            <div className="flex flex-col gap-2 rounded-md border border-line bg-white p-3.5">
              <span className={labelCls}>{t(`wizard:measurements.${key}`)}</span>
              <div className="flex gap-2">
                <input
                  className={`${inputCls} w-24 font-mono`}
                  type="number"
                  value={(entry.valueM as number) ?? ""}
                  onChange={(e) =>
                    e.target.value === ""
                      ? setM(key, null)
                      : setM(key, {
                          valueM: Number(e.target.value),
                          ...(key === "heightAgl" ? { reference: "landing" } : {}),
                        })
                  }
                />
                <select
                  className={inputCls}
                  value={(entry.method as string) ?? "estimate"}
                  onChange={(e) => setM(key, { method: e.target.value })}
                >
                  {["laser", "gps", "map", "estimate"].map((meth) => (
                    <option key={meth} value={meth}>{t(`wizard:measurements.methods.${meth}`)}</option>
                  ))}
                </select>
                <input
                  className={`${inputCls} w-32 font-mono`}
                  placeholder="2026-08"
                  value={(entry.measuredAt as string) ?? ""}
                  onChange={(e) => setM(key, { measuredAt: e.target.value })}
                />
              </div>
            </div>
          );
        };
        return (
          <div className="flex flex-col gap-4 p-5">
            <p className="text-sm text-muted">{t("wizard:measurements.hint")}</p>
            {row("rockdrop")}
            {row("heightAgl")}
            <label className="flex flex-col gap-1.5">
              <span className={labelCls}>{t("wizard:measurements.approachTime")}</span>
              <input
                className={`${inputCls} w-32 font-mono`}
                type="number"
                min={0}
                value={exit?.approachTimeMin ?? ""}
                onChange={(e) =>
                  setExit({ approachTimeMin: e.target.value === "" ? undefined : Number(e.target.value) })
                }
              />
            </label>
            <div className="flex gap-3">
              <button type="button" className={secondaryBtn} onClick={goNext}>{t("wizard:measurements.skip")}</button>
              <button type="button" className={`${primaryBtn} flex-1`} onClick={goNext}>{t("wizard:measurements.continue")}</button>
            </div>
          </div>
        );
      }

      case "landing":
        return (
          <div className="flex h-full flex-col">
            <div className="flex-1">
              <MapView
                center={exit && exit.lat !== 0 ? { lat: exit.lat, lon: exit.lon, zoom: 13 } : undefined}
                onPick={(lat, lon) =>
                  update((p) => {
                    const idx = p.features.findIndex((f) => f.role === "landing");
                    const feature: WizardFeature = {
                      ...(idx === -1 ? { role: "landing" as const, positionSource: "map" as const, surface: "grass" } : p.features[idx]),
                      lat,
                      lon,
                    } as WizardFeature;
                    if (idx === -1) p.features.push(feature);
                    else p.features[idx] = feature;
                    return p;
                  })
                }
                marker={landing ? { lat: landing.lat, lon: landing.lon } : null}
              />
            </div>
            <div className="flex flex-col gap-3 border-t border-line p-4">
              <p className="text-sm text-muted">{t("wizard:landing.hint")}</p>
              {landing && (
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm">{landing.lat.toFixed(5)}, {landing.lon.toFixed(5)}</span>
                  <select
                    className={inputCls}
                    value={landing.surface ?? "grass"}
                    onChange={(e) =>
                      update((p) => {
                        const idx = p.features.findIndex((f) => f.role === "landing");
                        if (idx !== -1) p.features[idx].surface = e.target.value;
                        return p;
                      })
                    }
                  >
                    {["grass", "talus", "water", "road", "forest", "other"].map((s) => (
                      <option key={s} value={s}>{t(`wizard:landing.surfaces.${s}`)}</option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex gap-3">
                {!landing && (
                  <button type="button" className={secondaryBtn} onClick={goNext}>{t("wizard:landing.skip")}</button>
                )}
                <button type="button" className={`${primaryBtn} flex-1`} disabled={false} onClick={goNext}>
                  {t("wizard:landing.continue")}
                </button>
              </div>
            </div>
          </div>
        );

      case "notes":
        return (
          <div className="flex flex-col gap-4 p-5">
            <p className="text-sm text-muted">{t("wizard:notes.hint")}</p>
            {(["observations", "hazards"] as const).map((key) => (
              <label key={key} className="flex flex-col gap-1.5">
                <span className={labelCls}>{t(`wizard:notes.${key}`)}</span>
                <textarea
                  className={`${inputCls} min-h-24`}
                  value={payload.notes?.[key] ?? ""}
                  onChange={(e) =>
                    update((p) => ({
                      ...p,
                      notes: { language: "fr", ...p.notes, [key]: e.target.value },
                    }))
                  }
                />
              </label>
            ))}
            <button type="button" className={primaryBtn} onClick={goNext}>{t("wizard:notes.continue")}</button>
          </div>
        );

      case "review": {
        const suitList = Object.entries(exit?.suitability ?? {})
          .filter(([, v]) => v)
          .map(([k]) => t(`object:suitability.${k}`))
          .join(" · ");
        return (
          <div className="flex flex-col gap-4 p-5">
            <div className="flex flex-col rounded-md border border-line bg-white">
              {[
                [t("wizard:review.position"), exit ? `${exit.lat.toFixed(5)}, ${exit.lon.toFixed(5)} · ${exit.positionSource}` : "—", "pin"],
                [t("wizard:review.details"), `${payload.object.name ?? payload.targetObjectPath ?? ""} — ${suitList}${exit?.exitDirectionDeg != null ? ` — ${exit.exitDirectionDeg}°` : ""}`, "details"],
                [t("wizard:review.landing"), landing ? `${landing.lat.toFixed(5)}, ${landing.lon.toFixed(5)} (${landing.surface})` : t("wizard:review.noLanding"), "landing"],
                [t("wizard:review.notes"), payload.notes?.observations || "—", "notes"],
              ].map(([label, value, target], i, arr) => (
                <div key={label as string} className={`flex items-center justify-between gap-3 px-4 py-3 ${i < arr.length - 1 ? "border-b border-[#eeece4]" : ""}`}>
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <span className="text-xs text-faint">{label}</span>
                    <span className="truncate text-sm font-medium">{value}</span>
                  </div>
                  <button type="button" onClick={() => setStep(target as Step)} className="text-sm font-semibold text-signal-dark">
                    {t("wizard:review.edit")}
                  </button>
                </div>
              ))}
            </div>
            <label className="flex items-start gap-3 rounded-md bg-granite p-4 text-paper">
              <input
                type="checkbox"
                checked={termsChecked}
                onChange={(e) => setTermsChecked(e.target.checked)}
                className="mt-1 h-5 w-5 accent-[#e84e10]"
              />
              <span className="flex flex-col gap-1.5">
                <span className="text-[13px] leading-relaxed">{t("wizard:review.terms")}</span>
                <span className="font-mono text-[11px] text-ondark-muted">
                  {t("wizard:review.termsVersion", { version: user?.current_terms_version })}
                </span>
              </span>
            </label>
            {submitError && (
              <div className="flex flex-col gap-1.5 rounded-md border border-[#e3b0ad] bg-[#fbe4e2] p-3.5 text-sm text-[#8f231d]">
                <strong>{t("wizard:result.errorTitle")}</strong>
                <span className="font-mono text-xs">{submitError.key}</span>
                {submitError.report
                  ?.filter((f) => f.level === "FAIL")
                  .map((f, i) => (
                    <span key={i} className="font-mono text-xs">{f.rule_id}: {f.message}</span>
                  ))}
              </div>
            )}
            <button type="button" className={primaryBtn} disabled={!termsChecked || busy} onClick={submit}>
              {busy ? t("wizard:review.submitting") : t("wizard:review.submit")}
            </button>
          </div>
        );
      }

      case "done":
        return (
          <div className="flex flex-col gap-5 p-6">
            <div className="flex items-center gap-3">
              <svg width="28" height="28" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="9" r="7.5" fill="#3a7d44" /><path d="M5.5 9 L8 11.5 L12.5 6.5" stroke="#ffffff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
              <h2 className="font-display text-2xl">{t("wizard:result.title")}</h2>
            </div>
            <p className="text-sm leading-relaxed text-muted">{t("wizard:result.body")}</p>
            <div className="flex flex-col gap-2 rounded-md border border-line bg-white p-4">
              <span className="font-mono text-xs tracking-[0.1em] text-faint">{t("wizard:result.reportTitle")}</span>
              {(result?.flags.no_landing as boolean) && (
                <span className="text-sm text-warntext">~ {t("wizard:review.noLanding")}</span>
              )}
              {(result?.flags.duplicate_override as boolean) && (
                <span className="font-mono text-sm text-warntext">~ duplicate_override</span>
              )}
              <span className="font-mono text-sm text-pass">PASS — {result?.publicId}</span>
            </div>
            <label className={`${secondaryBtn} cursor-pointer text-center`}>
              {t("wizard:result.addPhotos")}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && uploadPhoto(e.target.files[0])}
              />
            </label>
            {photoCount > 0 && <p className="text-sm text-pass">{t("wizard:result.photoAdded", { count: photoCount })}</p>}
            {photoError && <p className="text-sm text-[#8f231d]">{t("wizard:result.photoFailed", { key: photoError })}</p>}
            <Link to="/panel/submissions" className={`${primaryBtn} text-center`}>
              {t("wizard:result.toSubmissions")}
            </Link>
          </div>
        );
    }
  })();

  const containerClass = useMemo(
    () =>
      step === "pin" || step === "landing"
        ? "relative mx-auto flex h-[calc(100vh-76px)] w-full max-w-xl flex-col overflow-hidden"
        : "mx-auto w-full max-w-xl pb-16",
    [step],
  );

  return (
    <div className={containerClass}>
      {header}
      <div className={step === "pin" || step === "landing" ? "relative flex-1 overflow-hidden" : ""}>{body}</div>
    </div>
  );
}
