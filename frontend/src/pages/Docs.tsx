import { useParams, Link } from "react-router";
import Markdown from "react-markdown";

// Spec markdown is synced from ../specification/spec by scripts/sync-spec-docs.mjs
// (build-time copy — no cross-repo runtime dependency).
const docs = import.meta.glob("../content/spec/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const ORDER = ["openexits-2.0", "vocabularies", "rationale", "versioning", "annex-freeflight"];

function slugOf(path: string): string {
  return path.split("/").pop()!.replace(/\.md$/, "");
}

const bySlug = new Map(Object.entries(docs).map(([path, text]) => [slugOf(path), text]));
const slugs = [...ORDER.filter((s) => bySlug.has(s)), ...[...bySlug.keys()].filter((s) => !ORDER.includes(s))];

export default function Docs() {
  const { slug } = useParams();
  const active = slug && bySlug.has(slug) ? slug : slugs[0];
  const text = active ? bySlug.get(active) : undefined;
  return (
    <div className="flex flex-col gap-8 px-6 py-10 lg:flex-row lg:px-16">
      <nav className="flex shrink-0 flex-row flex-wrap gap-2 lg:w-56 lg:flex-col">
        {slugs.map((s) => (
          <Link
            key={s}
            to={`/docs/${s}`}
            className={
              s === active
                ? "rounded bg-ink px-3 py-2 font-mono text-[13px] text-paper"
                : "rounded px-3 py-2 font-mono text-[13px] text-muted hover:text-ink"
            }
          >
            {s}
          </Link>
        ))}
      </nav>
      <article className="prose-spec min-w-0 max-w-3xl flex-1">
        {text ? <Markdown>{text}</Markdown> : <p className="text-muted">…</p>}
      </article>
    </div>
  );
}
