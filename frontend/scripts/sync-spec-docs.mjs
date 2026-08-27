// Build-time copy of the specification's markdown into the frontend, so the
// docs pages have no cross-repo runtime dependency and cannot silently drift
// (CI re-runs this and diffs). Source of truth: ../specification/spec/*.md
import { copyFileSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const specDir = resolve(here, "../../../specification/spec");
const outDir = resolve(here, "../src/content/spec");

mkdirSync(outDir, { recursive: true });
let n = 0;
for (const name of readdirSync(specDir)) {
  if (!name.endsWith(".md")) continue;
  copyFileSync(join(specDir, name), join(outDir, name));
  n += 1;
}
console.log(`sync-spec-docs: copied ${n} file(s) from specification/spec`);
