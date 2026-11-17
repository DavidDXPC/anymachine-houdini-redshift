// Reference sheets for the lighting family (gen_sheets.mjs with a layout that also shows the fitting lit and unlit).
//   node rig2_blender/kit/lighting/gen_sheets_lighting.mjs [--only turn|detail] [--force] [id ...]
// Output: rig2_blender/kit/sheets/<id>_turn.png (views + unlit + lit), <id>_detail.png (guard, bracket, gland close-ups).
// Only ids of the "lighting" family are ever written. FAL_KEY from the environment, never printed.
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url)), KIT = path.join(HERE, '..'), TOOL = path.join(KIT, '..', '..', 'tools', 'detail_fal.mjs');
const OUT = path.join(KIT, 'sheets'), PR = path.join(OUT, 'prompts');
const M = JSON.parse(fs.readFileSync(path.join(KIT, 'manifest.json'), 'utf8'));
const LOOK = 'Look: a light fitting on a modern North Sea oil and gas platform, a real marine hazardous-area product, in service for some years and maintained. Real industrial construction: cast aluminium alloy bodies painted light grey or dark grey, thick glass, stainless steel clips and bolts, brass cable glands, galvanised steel brackets and conduit, black rubber cable. Light honest wear only: paint chipped on corners, a little salt dust, slight weathering of the glass. No heavy rust, no grime.';
const TURN = (a) => `A technical reference sheet for 3D modelling, showing ${a.what}${a.dims ? ` Real overall size about ${a.dims} metres (length x depth x height); keep those proportions.` : ''}

Layout: six separate views on a plain seamless mid-grey background, arranged in a tidy grid of three columns and two rows with clear space between them. Top row: front elevation, side elevation, back elevation, all with the lamp switched OFF. Bottom row: top plan view with the lamp OFF; a three-quarter view from the front and slightly above with the lamp switched OFF, showing how the unlit lens looks in daylight; and the same three-quarter view at dusk with the lamp switched ON, glowing, the lens bright, with a soft glow on the fitting's own guard and body. The elevation and plan views are true orthographic projections with no perspective, at the same scale; only the two three-quarter views have perspective. Every view shows the identical object: same parts, same colours, same wear.

Photographic, not a drawing: a real object photographed for 3D scanning, soft even diffuse studio light (except the lit view), no cast shadows on the background, sharp focus edge to edge, true-to-life materials. The whole object is inside each view with a margin. Nothing else in frame: no people, no room, no other objects.

${LOOK}

No text, no labels, no arrows, no dimension lines, no logos, no brand names, no watermark, no borders.`;
const DETAIL = (a) => `A reference sheet of close-up construction details, for a 3D modeller, of ${a.what}

Layout: six close-up photographs in a tidy grid of three columns and two rows on a plain mid-grey background with clear space between them. Each close-up shows a different part at about 10 to 25 cm across, square-on: (1) the guard or frame over the lens, showing how its wires or bars are joined and fixed to the body; (2) the lens or glass itself, unlit, showing its ribs or prisms and what is seen behind it; (3) the mounting bracket or foot, showing how it bolts to the surface; (4) the cable gland and the conduit or cable leaving the fitting; (5) a clip, hinge, pivot or fastener; (6) the same lens as in close-up 2 but switched on and glowing at dusk.

Photographic, soft even diffuse light, very sharp, true-to-life materials and real fastener sizes. Nothing else in frame.

${LOOK}

No text, no labels, no arrows, no logos, no brand names, no watermark, no borders.`;
const args = process.argv.slice(2); let only = null, force = false; const want = [];
while (args.length) { const a = args.shift(); if (a === '--only') only = args.shift(); else if (a === '--force') force = true; else want.push(a); }
const jobs = [];
for (const a of M.families.lighting) {
  if (want.length && !want.includes(a.id)) continue;
  for (const [kind, fn] of [['turn', TURN], ['detail', DETAIL]]) {
    if (only && only !== kind) continue;
    const out = path.join(OUT, `${a.id}_${kind}.png`);
    if (!force && fs.existsSync(out)) continue;
    jobs.push({ a, kind, out, prompt: fn(a) });
  }
}
fs.mkdirSync(PR, { recursive: true });
console.log(jobs.length, 'sheets to make');
const run = (j) => new Promise((done) => {
  const pf = path.join(PR, `${j.a.id}_${j.kind}.txt`); fs.writeFileSync(pf, j.prompt);
  const p = spawn(process.execPath, [TOOL, j.out, pf, '--size', 'landscape_16_9', '--model', 'sunburst'], { stdio: ['ignore', 'pipe', 'pipe'] });
  let log = ''; p.stdout.on('data', (d) => (log += d)); p.stderr.on('data', (d) => (log += d));
  p.on('close', (c) => { console.log(`${j.a.id}_${j.kind}: ${c === 0 ? 'ok' : 'FAILED ' + log.trim().slice(0, 200)}`); done(c === 0); });
});
let i = 0, bad = 0;
await Promise.all(Array.from({ length: 8 }, async () => { while (i < jobs.length) { const j = jobs[i++]; if (!(await run(j))) bad++; } }));
console.log('done,', bad, 'failed');
