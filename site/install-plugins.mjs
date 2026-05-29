// Workaround for a Quartz 5.0.0 bug: the bundled `npm run install-plugins`
// imports the full compiled config (which transitively imports .scss), and
// `tsx` cannot load .scss, so it crashes. We only need the list of plugin
// sources, so we read them straight out of quartz.config.yaml and call the
// git loader directly (gitLoader.ts has no .scss imports).
// Run with: npx tsx install-plugins.mjs
import fs from "fs"
import { parsePluginSource, installPlugins } from "./quartz/plugins/loader/gitLoader.ts"

const yaml = fs.readFileSync(new URL("./quartz.config.yaml", import.meta.url), "utf-8")
const sources = [...new Set([...yaml.matchAll(/source:\s*(github:[^\s#]+)/g)].map((m) => m[1]))]

console.log(`Installing ${sources.length} plugin(s) from Git...`)
const specs = sources.map(parsePluginSource)
const installed = await installPlugins(specs, { verbose: true })

if (installed.size === sources.length) {
  console.log(`✓ All ${installed.size} plugins installed successfully`)
} else {
  console.error(`✗ Only ${installed.size}/${sources.length} plugins installed`)
  process.exit(1)
}
