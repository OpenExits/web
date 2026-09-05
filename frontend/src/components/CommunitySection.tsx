import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { useAuth } from "../lib/auth";

interface Comment {
  id: number;
  handle: string;
  body: string;
  created_at: string;
}

interface CommunityData {
  object_id: string;
  comments: Comment[];
  confirmations: { last_confirmed_on: string | null; confirmations_12mo: number };
}

const CATEGORIES = ["position", "measurement", "access_status", "landing", "sensitive", "other"];

export default function CommunitySection({ objectPath }: { objectPath: string }) {
  const { t } = useTranslation("object");
  const { user, api } = useAuth();
  const [data, setData] = useState<CommunityData | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [reportCategory, setReportCategory] = useState<string | null>(null);
  const [reportBody, setReportBody] = useState("");
  const [reportSent, setReportSent] = useState(false);
  const [comment, setComment] = useState("");

  const refresh = useCallback(() => {
    fetch(`/api/v1/public/objects/${objectPath}/community`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => undefined);
  }, [objectPath]);

  useEffect(refresh, [refresh]);

  if (!data) return null;
  const conf = data.confirmations;

  async function doConfirm() {
    const r = await api(`/api/v1/objects/${data!.object_id}/confirm`, { method: "POST" });
    if (r.ok) {
      setConfirmed(true);
      refresh();
    }
  }

  async function sendReport() {
    if (!reportCategory) return;
    const r = await api(`/api/v1/objects/${data!.object_id}/report`, {
      method: "POST",
      body: JSON.stringify({ category: reportCategory, body: reportBody }),
    });
    if (r.ok) {
      setReportSent(true);
      setReportOpen(false);
    }
  }

  async function postComment() {
    if (!comment.trim()) return;
    const r = await api(`/api/v1/objects/${data!.object_id}/comments`, {
      method: "POST",
      body: JSON.stringify({ body: comment }),
    });
    if (r.ok) {
      setComment("");
      refresh();
    }
  }

  async function removeComment(id: number) {
    await api(`/api/v1/comments/${id}`, { method: "DELETE" });
    refresh();
  }

  return (
    <div className="flex flex-col gap-3">
      {/* confirmed-current + report */}
      <div className="flex items-center justify-between gap-3 rounded-md border border-line bg-white px-3.5 py-3">
        <div className="flex flex-col gap-0.5">
          <span className="flex items-center gap-2 text-[13px] font-bold">
            <svg width="15" height="15" viewBox="0 0 18 18" fill="none" aria-hidden>
              <circle cx="9" cy="9" r="7.5" fill={conf.last_confirmed_on ? "#3a7d44" : "#b0aca0"} />
              <path d="M5.5 9 L8 11.5 L12.5 6.5" stroke="#ffffff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {conf.last_confirmed_on
              ? t("community.lastConfirmed", { date: conf.last_confirmed_on })
              : t("community.neverConfirmed")}
          </span>
          <span className="text-[11px] text-faint">
            {t("community.count12mo", { count: conf.confirmations_12mo })}
          </span>
        </div>
        {user && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={doConfirm}
              disabled={confirmed}
              className="rounded bg-ink px-3 py-2 text-xs font-bold text-paper disabled:opacity-60"
            >
              {confirmed ? t("community.confirmed") : t("community.confirm")}
            </button>
            <button
              type="button"
              onClick={() => setReportOpen((o) => !o)}
              className="rounded border-[1.5px] border-line px-3 py-2 text-xs font-semibold text-muted"
            >
              {t("community.report")}
            </button>
          </div>
        )}
      </div>

      {reportSent && <p className="text-xs font-semibold text-pass">{t("community.reportSent")}</p>}
      {reportOpen && (
        <div className="flex flex-col gap-2.5 rounded-md border border-line bg-white p-3.5">
          <span className="text-sm font-bold">{t("community.reportTitle")}</span>
          <div className="flex flex-col gap-1.5">
            {CATEGORIES.map((c) => (
              <label key={c} className="flex items-center gap-2 text-[13px]">
                <input
                  type="radio"
                  name="report-category"
                  checked={reportCategory === c}
                  onChange={() => setReportCategory(c)}
                  className="accent-[#e84e10]"
                />
                {t(`community.categories.${c}`)}
              </label>
            ))}
          </div>
          <textarea
            className="min-h-16 rounded border border-line px-3 py-2 text-sm outline-none focus:border-ink"
            placeholder={t("community.reportBody")}
            value={reportBody}
            onChange={(e) => setReportBody(e.target.value)}
          />
          <button
            type="button"
            onClick={sendReport}
            disabled={!reportCategory}
            className="rounded bg-signal py-2.5 text-sm font-bold text-white disabled:opacity-50"
          >
            {t("community.reportSend")}
          </button>
        </div>
      )}

      {/* discussion */}
      <div className="flex flex-col gap-2.5 rounded-md border border-line bg-white p-3.5">
        <div className="flex items-center justify-between">
          <span className="text-sm font-bold">{t("community.discussion")}</span>
          <span className="font-mono text-[11px] text-faint">
            {t("community.messages", { count: data.comments.length })}
          </span>
        </div>
        <p className="text-[11px] leading-relaxed text-faint">{t("community.composerHint")}</p>
        {data.comments.map((c) => (
          <div key={c.id} className="flex flex-col gap-1 rounded bg-[#f7f5ef] px-3 py-2">
            <span className="flex items-center justify-between text-[11px] text-faint">
              <span className="font-semibold text-muted">@{c.handle}</span>
              <span className="flex items-center gap-2">
                {c.created_at.slice(0, 10)}
                {user && (user.handle === c.handle || user.role !== "user") && (
                  <button type="button" onClick={() => removeComment(c.id)} className="text-[#8f231d]">
                    {t("community.delete")}
                  </button>
                )}
              </span>
            </span>
            <p className="text-[13px] leading-relaxed">{c.body}</p>
          </div>
        ))}
        {user ? (
          <div className="flex flex-col gap-1.5">
            <div className="flex gap-2">
              <input
                className="flex-1 rounded border border-line px-3 py-2 text-sm outline-none focus:border-ink"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <button
                type="button"
                onClick={postComment}
                className="rounded bg-ink px-4 py-2 text-sm font-bold text-paper"
              >
                {t("community.post")}
              </button>
            </div>
            <span className="text-[11px] text-warntext">{t("community.composerWarning")}</span>
          </div>
        ) : (
          <Link to="/panel" className="text-[13px] font-semibold text-signal-dark">
            {t("community.signInToPost")}
          </Link>
        )}
      </div>
    </div>
  );
}
