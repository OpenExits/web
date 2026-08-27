import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../lib/auth";

interface SubmissionSummary {
  public_id: string;
  kind: string;
  status: string;
  site_name: string | null;
  target_site_id: string | null;
  created_at: string;
  published_site_id: string | null;
}

interface Message {
  id: number;
  author_user_id: number;
  body: string;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-[#eee9db] text-warntext",
  changes_requested: "bg-warnbg text-warntext",
  approved: "bg-[#e5efe0] text-pass",
  publishing: "bg-[#e5efe0] text-pass",
  publish_failed: "bg-[#fbe4e2] text-[#8f231d]",
  published: "bg-[#e5efe0] text-pass",
  rejected: "bg-[#fbe4e2] text-[#8f231d]",
  withdrawn: "bg-[#f4f2ec] text-faint",
};

export default function Submissions() {
  const { t } = useTranslation("common");
  const { api } = useAuth();
  const [subs, setSubs] = useState<SubmissionSummary[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [reply, setReply] = useState("");

  const refresh = useCallback(() => {
    api("/api/v1/submissions")
      .then((r) => r.json())
      .then((body) => setSubs(body.submissions ?? []))
      .catch(() => undefined);
  }, [api]);

  useEffect(refresh, [refresh]);

  const openDetail = useCallback(
    (pid: string) => {
      setOpen(pid);
      api(`/api/v1/submissions/${pid}`)
        .then((r) => r.json())
        .then((body) => setMessages(body.submission?.messages ?? []))
        .catch(() => setMessages([]));
    },
    [api],
  );

  async function withdraw(pid: string) {
    await api(`/api/v1/submissions/${pid}/withdraw`, { method: "POST" });
    refresh();
  }

  async function sendReply(pid: string) {
    if (!reply.trim()) return;
    await api(`/api/v1/submissions/${pid}/messages`, {
      method: "POST",
      body: JSON.stringify({ body: reply }),
    });
    setReply("");
    openDetail(pid);
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-4 px-5 py-10">
      <h1 className="font-display text-3xl">{t("submissions.title")}</h1>
      {subs.length === 0 && <p className="text-muted">{t("submissions.empty")}</p>}
      {subs.map((sub) => (
        <div key={sub.public_id} className="rounded-md border border-line bg-white">
          <button
            type="button"
            onClick={() => (open === sub.public_id ? setOpen(null) : openDetail(sub.public_id))}
            className="flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left"
          >
            <span className="flex flex-col gap-0.5">
              <span className="text-[15px] font-bold">
                {sub.site_name ?? sub.target_site_id ?? sub.public_id}
              </span>
              <span className="text-xs text-faint">
                {sub.kind} · {sub.created_at.slice(0, 10)}
              </span>
            </span>
            <span className={`rounded px-2.5 py-1 text-xs font-bold ${STATUS_COLORS[sub.status] ?? ""}`}>
              {t(`submissions.status.${sub.status}`)}
            </span>
          </button>
          {open === sub.public_id && (
            <div className="flex flex-col gap-3 border-t border-[#eeece4] p-4">
              {messages.length > 0 && (
                <div className="flex flex-col gap-2">
                  <span className="font-mono text-xs tracking-[0.1em] text-faint">
                    {t("submissions.messages").toUpperCase()}
                  </span>
                  {messages.map((m) => (
                    <p key={m.id} className="rounded bg-[#f7f5ef] px-3 py-2 text-sm">{m.body}</p>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <input
                  className="flex-1 rounded border border-line px-3 py-2 text-sm outline-none focus:border-ink"
                  placeholder={t("submissions.reply")}
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => sendReply(sub.public_id)}
                  className="rounded bg-ink px-4 py-2 text-sm font-bold text-paper"
                >
                  {t("submissions.send")}
                </button>
              </div>
              {(sub.status === "pending" || sub.status === "changes_requested") && (
                <button
                  type="button"
                  onClick={() => withdraw(sub.public_id)}
                  className="self-start text-sm font-semibold text-[#8f231d]"
                >
                  {t("submissions.withdraw")}
                </button>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
