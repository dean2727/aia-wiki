// Workaround for a Quartz 5.0.0 bug: the bundled `npm run install-plugins`
// imports the full compiled config (which transitively imports .scss), and
// `tsx` cannot load .scss, so it crashes. We only need the list of plugin
// sources, so we read them straight out of quartz.config.yaml and call the
// git loader directly (gitLoader.ts has no .scss imports).
//
// This also compiles the local plugins under ./quartz-plugins. Quartz's own
// build is bundled by esbuild but imports plugins at runtime with a plain
// dynamic import, so a plugin has to ship JavaScript — Node cannot parse the
// TypeScript sources. Compiling here means the deploy workflow, which already
// runs this file before `npx quartz build`, needs no changes and dist/ never
// has to be committed.
// Run with: npx tsx install-plugins.mjs
import fs from "fs"
import path from "path"
import { fileURLToPath } from "url"
import esbuild from "esbuild"
import { parsePluginSource, installPlugins } from "./quartz/plugins/loader/gitLoader.ts"

const siteDir = path.dirname(fileURLToPath(import.meta.url))
const yaml = fs.readFileSync(path.join(siteDir, "quartz.config.yaml"), "utf-8")
const sources = [...new Set([...yaml.matchAll(/source:\s*(github:[^\s#]+)/g)].map((m) => m[1]))]

console.log(`Installing ${sources.length} plugin(s) from Git...`)
const specs = sources.map(parsePluginSource)
const installed = await installPlugins(specs, { verbose: true })

if (installed.size !== sources.length) {
  console.error(`✗ Only ${installed.size}/${sources.length} plugins installed`)
  process.exit(1)
}
console.log(`✓ All ${installed.size} plugins installed successfully`)

const localDir = path.join(siteDir, "quartz-plugins")
const localPlugins = fs.existsSync(localDir)
  ? fs.readdirSync(localDir, { withFileTypes: true }).filter((entry) => entry.isDirectory())
  : []

for (const plugin of localPlugins) {
  const root = path.join(localDir, plugin.name)
  const entries = ["index.ts", "component.tsx"]
    .map((file) => path.join(root, file))
    .filter((file) => fs.existsSync(file))
  if (entries.length === 0) continue

  await esbuild.build({
    entryPoints: entries,
    outdir: path.join(root, "dist"),
    bundle: true,
    format: "esm",
    platform: "node",
    target: "node22",
    jsx: "automatic",
    jsxImportSource: "preact",
    logLevel: "warning",
    // Preact must stay the singleton the rest of the build uses, and the relative
    // ../../quartz/* type imports are erased, so nothing else needs bundling.
    external: ["preact", "preact/*", "vfile", "unified"],
  })
  console.log(`✓ Compiled local plugin ${plugin.name}`)
}

// Local plugins are symlinked, so install them after compiling to keep the
// loader from resolving an entry point that does not exist yet.
const localSources = [...new Set([...yaml.matchAll(/source:\s*(\.\/[^\s#]+)/g)].map((m) => m[1]))]
if (localSources.length > 0) {
  const localSpecs = localSources.map((source) => parsePluginSource(path.join(siteDir, source.slice(2))))
  const localInstalled = await installPlugins(localSpecs, { verbose: true })
  console.log(`✓ Linked ${localInstalled.size}/${localSources.length} local plugin(s)`)
}
