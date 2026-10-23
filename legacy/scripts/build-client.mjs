#!/usr/bin/env node
/**
 * Build the served Client half from the source template.
 *
 *   node scripts/build-client.mjs
 *
 * Reads `src/client.src.js`, replaces the `__FISH_B64__` token with the base64
 * of `assets/fish.png` (as written by the asset pipeline into
 * `assets/fish.b64.txt`), and writes `client.js` — the file the Harness Client
 * module loader serves for this bundle.
 *
 * The image is embedded rather than served from a route so the widget renders on
 * the first frame without a second authenticated request, and so a plugin update
 * cannot leave the widget pointing at a stale asset path.
 */

import { readFile, writeFile, stat } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const TEMPLATE = join(root, 'src', 'client.src.js')
const OUT = join(root, 'client.js')
const PNG = join(root, 'assets', 'fish.png')
const B64 = join(root, 'assets', 'fish.b64.txt')
const TOKEN = '__FISH_B64__'
/** The Client artifact serving limit is generous, but keep the payload lean. */
const MAX_OUT_BYTES = 600 * 1024

async function main() {
  const template = await readFile(TEMPLATE, 'utf8')
  if (!template.includes(TOKEN)) throw new Error(`${TEMPLATE} no longer contains ${TOKEN}`)

  let base64
  try {
    base64 = (await readFile(B64, 'utf8')).trim()
  } catch {
    const bytes = await readFile(PNG)
    base64 = bytes.toString('base64')
  }
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(base64) || base64.length < 64) {
    throw new Error(`${B64} does not look like a base64 PNG body`)
  }

  const built = template.split(TOKEN).join(base64)
  if (built.includes(TOKEN)) throw new Error('placeholder survived the replacement')
  await writeFile(OUT, built, 'utf8')

  const pngInfo = await stat(PNG)
  const outInfo = await stat(OUT)
  if (outInfo.size > MAX_OUT_BYTES) throw new Error(`client.js is ${outInfo.size} bytes; the cap is ${MAX_OUT_BYTES}`)
  console.log(`built ${OUT}`)
  console.log(`  fish.png   ${pngInfo.size} bytes, ${base64.length} base64 chars`)
  console.log(`  client.js  ${outInfo.size} bytes`)
}

main().catch((error) => {
  console.error(`build failed: ${error instanceof Error ? error.message : String(error)}`)
  process.exitCode = 1
})
