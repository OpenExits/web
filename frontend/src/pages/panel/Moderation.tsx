import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../lib/auth";

type Lane = "pending" | "changes_requested" | "publish_failed" | "reports";

interface QueueRow {
  public_id: string;
  kind: string;
  status: string;
  object_name: string | null;
  target_object_id: string | null;
  created_at: string;
  contributor: string;
  contributor_published: number;
  flags: { duplicate_override: boolean; no_landing: boolean; validator_warns: number };
}

interface Report {
  id: number;
  object_id: string;
  category: string;
  body: string | null;
  reporter: string;
  created_at: string;
}

interface Finding { rule_id: string; level: string; message: string }

interface Detail {
  public_id: string;
  status: string;
  contributor: string;
  normalized: Record<string, unknown> | null;
  payload: { notes?: Record<string, string> };
  machine_flags: { validator: Finding[] };
  media: { sha256: string }[];
  messages: { id: number; body: string; visibility: string }[];
}

const chip = "rounded px-2 py-0.5 text-[11px] font-bold";

export default function Moderation() {
  const { t } = useTranslation(["moderation", "object"]);
  const { user, api } = useAuth();
  const [lane, setLane] = useState<Lane>("pending");
  const [rows, setRows] = useState<QueueRow[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [jsonDraft, setJsonDraft] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [gateReport, setGateReport] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState("");

  const refresh = useCallback(() => {
    if (lane === "reports") {
      api("/api/v1/moderation/reports")
        .then((r) => r.json())
        .then((b) => setReports(b.reports ?? []));
    } else {
      api(`/api/v1/moderation/queue?status=${lane}`)
        .then((r) => r.json())
        .then((b) => setRows(b.queue ?? []));
    }
  }, [api, lane]);

  useEffect(() => {
    setOpen(null);
    setDetail(null);
    setGateReport(null);
    refresh();
  }, [refresh]);

  const openDetail = useCallback(
    (pid: string) => {
      setOpen(pid);
      setNotice(null);
      setGateReport(null);
      api(`/api/v1/moderation/submissions/${pid}`)
        .then((r) => r.json())
        .then((b) => {
          setDetail(b.submission);
          setJsonDraft(JSON.stringify(b.submission.normalized, null, 2));
        });
    },
    [api],
  );

  if (user && user.role === "user") {
    return <p className="p-16 text-center text-muted">{t("moderation:forbidden")}</p>;
  }

  async function act(pid: string, path: string, body?: unknown) {
    setBusy(true);
    setGateReport(null);
    const r = await api(`/api/v1/moderation/submissions/${pid}/${path}`, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
    const resp = await r.json();
    setBusy(false);
    if (resp.publish) {
      if (resp.publish.ok) {
        setNotice(t("moderation:detail.publishOk", { object: resp.publish.object, sha: resp.publish.sha?.slice(0, 10) }));
      } else {
        setNotice(t("moderation:detail.publishFailed"));
        setGateReport(resp.publish.report ?? resp.publish.key);
      }
    }
    refresh();
    if (resp.submission?.status && open) openDetail(pid);
  }

  async function saveJson(pid: string) {
    try {
      const doc = JSON.parse(jsonDraft);
      const r = await api(`/api/v1/moderation/submissions/${pid}/normalized`, {
        method: "PUT",
        body: JSON.stringify(doc),
      });
      const resp = await r.json();
      setNotice(r.ok ? t("moderation:detail.saved") : JSON.stringify(resp.report ?? resp.error));
    } catch {
      setNotice("invalid JSON");
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-5 py-10">
      <h1 className="font-display text-3xl">{t("moderation:title")}</h1>
      <div className="flex gap-2">
        {(["pending", "changes_requested", "publish_failed", "reports"] as Lane[]).map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => setLane(l)}
            className={
              lane === l
                ? "rounded bg-ink px-3.5 py-2 text-[13px] font-semibold text-paper"
                : "rounded border border-line px-3.5 py-2 text-[13px] font-medium text-muted"
            }
          >
            {t(`moderation:lanes.${l}`)}
          </button>
        ))}
      </div>

      {lane === "reports" ? (
        <div className="flex flex-col gap-2.5">
          {reports.length === 0 && <p className="text-muted">{t("moderation:reports.empty")}</p>}
          {reports.map((r) => (
            <div key={r.id} className="flex items-center justify-between gap-3 rounded-md border border-line bg-white px-4 py-3">
              <div className="flex flex-col gap-0.5">
                <span className={`self-start ${chip} ${r.category === "sensitive" ? "bg-[#fbe4e2] text-[#8f231d]" : "bg-[#eee9db] text-warntext"}`}>
                  {t(`object:community.categories.${r.category}`)}
                </span>
                <span className="text-sm">{r.body ?? "—"}</span>
                <span className="text-xs text-faint">
                  {t("moderation:reports.by", { handle: r.reporter })} · {r.created_at.slice(0, 10)} ·{" "}
                  <span className="font-mono">{r.object_id.slice(0, 10)}…</span>
                </span>
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => api(`/api/v1/moderation/reports/${r.id}/resolve`, { method: "POST" }).then(refresh)} className="rounded bg-pass px-3 py-2 text-xs font-bold text-white">
                  {t("moderation:reports.resolve")}
                </button>
                <button type="button" onClick={() => api(`/api/v1/moderation/reports/${r.id}/dismiss`, { method: "POST" }).then(refresh)} className="rounded border border-line px-3 py-2 text-xs font-semibold text-muted">
                  {t("moderation:reports.dismiss")}
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {rows.map((row) => (
            <div key={row.public_id} className="rounded-md border border-line bg-white">
              <button
                type="button"
                onClick={() => (open === row.public_id ? setOpen(null) : openDetail(row.public_id))}
                className="flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left"
              >
                <span className="flex flex-col gap-1">
                  <span className="text-[15px] font-bold">
                    {row.object_name ?? row.target_object_id}
                    <span className="ml-2 rounded bg-ink px-2 py-0.5 text-[10px] font-bold text-paper">
                      {row.kind.replace("_", " ").toUpperCase()}
                    </span>
                  </span>
                  <span className="text-xs text-faint">
                    {t("moderation:contributorMeta", { handle: `@${row.contributor}`, count: row.contributor_published })}
                    {" · "}{row.created_at.slice(0, 10)}
                  </span>
                  <span className="flex gap-1.5">
                    {row.flags.duplicate_override && <span className={`${chip} bg-[#fbe4e2] text-[#8f231d]`}>{t("moderation:flags.duplicate_override")}</span>}
                    {row.flags.no_landing && <span className={`${chip} bg-warnbg text-warntext`}>{t("moderation:flags.no_landing")}</span>}
                    {row.flags.validator_warns > 0 && <span className={`${chip} bg-[#eee9db] text-warntext`}>{t("moderation:flags.validator_warns", { count: row.flags.validator_warns })}</span>}
                  </span>
                </span>
              </button>

              {open === row.public_id && detail && (
                <div className="flex flex-col gap-3.5 border-t border-[#eeece4] p-4">
                  <p className="rounded border border-warnline bg-warnbg px-3 py-2 text-xs text-warntext">
                    {t("moderation:sensitivity")}
                  </p>
                  {/* What approving does and does not assert. Kept beside the
                      approve control rather than buried in the governance doc,
                      because it is the moment the question actually arises. */}
                  <p className="rounded border border-line bg-[#f4f2ec] px-3 py-2 text-xs text-[#4a4c46]">
                    {t("moderation:scope")}
                  </p>
                  {notice && <p className="text-sm font-semibold">{notice}</p>}
                  {gateReport && (
                    <pre className="max-h-64 overflow-auto rounded bg-ink p-3 font-mono text-[11px] text-[#e8b34b]">{gateReport}</pre>
                  )}
                  {detail.machine_flags.validator.length > 0 && (
                    <div className="rounded bg-ink p-3 font-mono text-[11px]">
                      {detail.machine_flags.validator.map((f, i) => (
                        <div key={i} className={f.level === "FAIL" ? "text-[#e88b5f]" : "text-[#e8b34b]"}>
                          {f.level} {f.rule_id}: {f.message}
                        </div>
                      ))}
                    </div>
                  )}
                  {detail.payload.notes && (
                    <p className="rounded bg-[#f7f5ef] px-3 py-2 text-sm italic">
                      {Object.entries(detail.payload.notes).filter(([k]) => k !== "language").map(([, v]) => v).join(" — ")}
                    </p>
                  )}
                  {detail.media.length > 0 && (
                    <div className="flex gap-2">
                      {detail.media.map((m) => (
                        <img key={m.sha256} src={`/api/v1/media/${m.sha256}`} alt="" className="h-20 w-28 rounded object-cover" />
                      ))}
                    </div>
                  )}
                  <details>
                    <summary className="cursor-pointer text-xs font-semibold text-muted">
                      {t("moderation:detail.editHint")}
                    </summary>
                    <textarea
                      className="mt-2 min-h-48 w-full rounded border border-line p-2 font-mono text-xs"
                      value={jsonDraft}
                      onChange={(e) => setJsonDraft(e.target.value)}
                    />
                    <button type="button" onClick={() => saveJson(row.public_id)} className="mt-1 rounded border border-line px-3 py-1.5 text-xs font-semibold">
                      {t("moderation:detail.save")}
                    </button>
                  </details>
                  {detail.messages.length > 0 && (
                    <div className="flex flex-col gap-1.5">
                      {detail.messages.map((m) => (
                        <p key={m.id} className="rounded bg-[#f7f5ef] px-3 py-1.5 text-sm">{m.body}</p>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-2">
                    <input
                      className="flex-1 rounded border border-line px-3 py-2 text-sm outline-none focus:border-ink"
                      placeholder={t("moderation:detail.reply")}
                      value={reply}
                      onChange={(e) => setReply(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={async () => {
                        if (!reply.trim()) return;
                        await api(`/api/v1/submissions/${row.public_id}/messages`, { method: "POST", body: JSON.stringify({ body: reply }) });
                        setReply("");
                        openDetail(row.public_id);
                      }}
                      className="rounded bg-ink px-3.5 py-2 text-sm font-bold text-paper"
                    >
                      {t("moderation:detail.send")}
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2.5">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => act(row.public_id, row.status === "publish_failed" ? "publish" : "approve")}
                      className="rounded bg-pass px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
                    >
                      {busy
                        ? t("moderation:detail.publishing")
                        : row.status === "publish_failed"
                          ? t("moderation:detail.retry")
                          : t("moderation:detail.approve")}
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        const msg = window.prompt(t("moderation:detail.messagePrompt"));
                        if (msg) act(row.public_id, "request-changes", { message: msg });
                      }}
                      className="rounded border-[1.5px] border-ink px-4 py-2.5 text-sm font-semibold"
                    >
                      {t("moderation:detail.requestChanges")}
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        const reason = window.prompt(t("moderation:detail.reasonPrompt"));
                        if (reason !== null) act(row.public_id, "reject", { reason });
                      }}
                      className="rounded border-[1.5px] border-line px-4 py-2.5 text-sm font-semibold text-muted"
                    >
                      {t("moderation:detail.reject")}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
