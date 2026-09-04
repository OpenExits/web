// Give every known route a real file, so a static host answers 200 instead of 404.
//
// GitHub Pages has no SPA rewrite: it serves 404.html for unknown paths, which
// renders the app correctly but with a 404 status. Users see the right page and
// never notice; crawlers see "not found" and drop /docs, /map and every spec
// page from the index. For a project whose whole purpose is being the findable
// canonical source of a standard, that is the wrong failure to leave in place.
//
// Every route here is static and known at build time, so each one gets its own
// index.html. 404.html stays as the fallback for genuinely unknown paths, which
// is exactly what it should be.
import { copyFileSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, "../dist");
const specDir = resolve(here, "../src/content/spec");
const source = join(dist, "index.html");

const routes = ["docs", "map", "panel", "terms"];

for (const name of readdirSync(specDir)) {
  if (name.endsWith(".md")) routes.push(`docs/${name.replace(/\.md$/, "")}`);
}

for (const route of routes) {
  const dir = join(dist, route);
  mkdirSync(dir, { recursive: true });
  copyFileSync(source, join(dir, "index.html"));
}

console.log(`emit-route-pages: wrote ${routes.length} route page(s): ${routes.join(", ")}`);
