// Build-time copy of the specification's markdown into the frontend, so the docs
// pages have no cross-repo runtime dependency and cannot silently drift.
//
// Two sources, in order:
//   1. A sibling ../../../specification/spec checkout, when working on both repos
//      at once. Fast, offline, and reflects uncommitted spec edits immediately.
//   2. The pinned specification tag, fetched over HTTPS.
//
// Source 2 is what makes this repository buildable on its own. Without it a
// fresh clone of `web` could not build at all -- it silently required a sibling
// checkout that only existed on one machine, which is exactly how CI failed the
// first time it ran.
//
// SPEC_TAG is pinned rather than tracking main for the same reason
// commons/ci/requirements.txt pins the validator: the docs a build ships must
// correspond to a specific published version of the standard.
import { copyFileSync, existsSync, mkdirSync, readdirSync, unlinkSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SPEC_REPO = "OpenExits/specification";
const SPEC_TAG = "v2.0.2";

const here = dirname(fileURLToPath(import.meta.url));
const siblingDir = resolve(here, "../../../specification/spec");
const outDir = resolve(here, "../src/content/spec");

mkdirSync(outDir, { recursive: true });

// Start from an empty directory: a document withdrawn from the specification
// (the freeflight annex, for one) must not linger from an earlier sync and
// ship as a docs page from a local checkout.
for (const name of readdirSync(outDir)) {
  if (name.endsWith(".md")) unlinkSync(join(outDir, name));
}

function fromSibling() {
  let n = 0;
  for (const name of readdirSync(siblingDir)) {
    if (!name.endsWith(".md")) continue;
    copyFileSync(join(siblingDir, name), join(outDir, name));
    n += 1;
  }
  return n;
}

async function fromTag() {
  const api = `https://api.github.com/repos/${SPEC_REPO}/contents/spec?ref=${SPEC_TAG}`;
  const headers = { Accept: "application/vnd.github+json", "User-Agent": "openexits-build" };
  if (process.env.GITHUB_TOKEN) headers.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`;

  const listing = await fetch(api, { headers });
  if (!listing.ok) {
    throw new Error(`listing ${SPEC_REPO}@${SPEC_TAG}/spec failed: ${listing.status} ${listing.statusText}`);
  }
  const entries = await listing.json();
  let n = 0;
  for (const entry of entries) {
    if (entry.type !== "file" || !entry.name.endsWith(".md")) continue;
    const raw = await fetch(entry.download_url, { headers: { "User-Agent": "openexits-build" } });
    if (!raw.ok) throw new Error(`fetch ${entry.name} failed: ${raw.status}`);
    writeFileSync(join(outDir, entry.name), await raw.text(), "utf8");
    n += 1;
  }
  return n;
}

let count = 0;
let source = "";

if (existsSync(siblingDir)) {
  count = fromSibling();
  source = "sibling checkout (../specification/spec)";
} else {
  count = await fromTag();
  source = `${SPEC_REPO}@${SPEC_TAG}`;
}

if (count === 0) {
  console.error(`sync-spec-docs: no .md files found via ${source}`);
  process.exit(1);
}
console.log(`sync-spec-docs: copied ${count} file(s) from ${source}`);
