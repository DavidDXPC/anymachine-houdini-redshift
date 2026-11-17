// Reference sheets for every Oil Rig V2 component that is modelled, generated or scripted (not the reused rig 1 props):
// a turnaround sheet (front, back, sides, top, three-quarter) and a sheet of close-up construction details.
// The look comes from the approved reference the component appears in (first entry of its "refs"), passed as input.
//   node rig2_blender/kit/gen_sheets.mjs [--only turn|detail] [--force] [id ...]
// Output: rig2_blender/kit/sheets/<id>_turn.png, <id>_detail.png. Skips files that exist. FAL_KEY from the environment, never printed.
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url)), TOOL = path.join(HERE, '..', '..', 'tools', 'detail_fal.mjs');
const REFS = path.join(HERE, '..', 'concepts', 'out', 'v5_ref', 'bypass'), OUT = path.join(HERE, 'sheets'), PR = path.join(OUT, 'prompts');
const M = JSON.parse(fs.readFileSync(path.join(HERE, 'manifest.json'), 'utf8'));
const LOOK = 'Look: equipment on a modern North Sea oil and gas platform, maintained and repainted within the last few years. Real industrial construction: steel plate, rolled sections, weld seams, bolted joints, real fasteners at real size. Paint is marine two-pack: soft off-white and light grey for structures, slightly dull ochre safety yellow for rails, stairs and guards, dark blue for containers, muted green, blue and red for pipes, orange or blue for machinery skids, galvanised zinc for grating. Light honest wear only: paint chipped to primer on corners and edges, scuffs, a few touch-up patches, a little salt dust, a few hand-sized rust blooms at welds and bolts. No heavy rust, no grime, no mud.';
const WITH = (a) => (a.refs?.length ? 'The input image is a photograph of the platform this object belongs to; the object appears in it. Take its colours, materials, proportions and condition from that photograph, but show only the one object, complete, on its own.' : '');
const TURN = (a) => `A technical reference sheet for 3D modelling, showing ONE object from six directions: ${a.what}.${a.dims ? ` Its real size is ${a.dims} metres (length x width x height); keep those proportions exactly.` : ''}

Layout: six separate views of the same single object on a plain seamless light-grey background, arranged in a tidy grid of three columns and two rows with clear space between them. Top row: front elevation, left side elevation, back elevation. Bottom row: right side elevation, top plan view, three-quarter view from the front and slightly above. The five elevation and plan views are true orthographic projections with no perspective at all, drawn at the same scale and standing on a common ground line; only the three-quarter view has perspective. Every view shows the identical object: same parts, same colours, same damage.

Photographic, not a drawing: a real object photographed for 3D scanning, soft even diffuse studio light, no cast shadows on the background, sharp focus edge to edge, true-to-life materials. The whole object is inside each view with a margin. Nothing else in frame: no people, no floor, no room, no other objects.

${WITH(a)}

${LOOK}

No text, no labels, no arrows, no dimension lines, no logos, no brand names, no watermark, no borders.`;
const DETAIL = (a) => `A reference sheet of close-up construction details of ONE object, for a 3D modeller: ${a.what}.

Layout: six close-up photographs in a tidy grid of three columns and two rows on a plain light-grey background with clear space between them. Each close-up shows a different part of the same object at about 30 to 60 cm across, square-on: (1) a corner, showing how the edges meet; (2) a typical joint or seam, showing welds, bolts or rivets and their spacing; (3) the base or foot, showing how it stands on or fixes to the deck; (4) a functional detail such as a hinge, latch, handle, clamp, flange or bracket; (5) a typical area of plain surface, showing the paint texture, panel pressing or ribbing; (6) the most worn spot, showing chipped paint and scuffing.

Photographic, soft even diffuse light, very sharp, true-to-life materials and real fastener sizes. Nothing else in frame.

${WITH(a)}

${LOOK}

No text, no labels, no arrows, no logos, no brand names, no watermark, no borders.`;

const args = process.argv.slice(2); let only = null, force = false; const want = [];
while (args.length) { const a = args.shift(); if (a === '--only') only = args.shift(); else if (a === '--force') force = true; else want.push(a); }
const all = Object.entries(M.families).flatMap(([family, list]) => list.map((a) => ({ ...a, family }))).filter((a) => a.track !== 'reuse');
const jobs = [];
for (const a of all) {
  if (want.length && !want.includes(a.id)) continue;
  for (const [kind, fn] of [['turn', TURN], ['detail', DETAIL]]) {
    if (only && only !== kind) continue;
    if (kind === 'detail' && a.track === 'generate') continue; // image-to-3D takes the turnaround only
    const out = path.join(OUT, `${a.id}_${kind}.png`);
    if (!force && fs.existsSync(out)) continue;
    jobs.push({ a, kind, out, prompt: fn(a) });
  }
}
fs.mkdirSync(PR, { recursive: true });
console.log(jobs.length, 'sheets to make');
const run = (j) => new Promise((done) => {
  const pf = path.join(PR, `${j.a.id}_${j.kind}.txt`); fs.writeFileSync(pf, j.prompt);
  const ref = j.a.refs?.[0] && path.join(REFS, j.a.refs[0] + '.png');
  const p = spawn(process.execPath, [TOOL, j.out, pf, '--size', 'landscape_16_9', '--model', 'sunburst', ...(ref && fs.existsSync(ref) ? [ref] : [])], { stdio: ['ignore', 'pipe', 'pipe'] });
  let log = ''; p.stdout.on('data', (d) => (log += d)); p.stderr.on('data', (d) => (log += d));
  p.on('close', (c) => { console.log(`${j.a.id}_${j.kind}: ${c === 0 ? 'ok' : 'FAILED ' + log.trim().slice(0, 200)}`); done(c === 0); });
});
let i = 0, bad = 0;
await Promise.all(Array.from({ length: 10 }, async () => { while (i < jobs.length) { const j = jobs[i++]; if (!(await run(j))) bad++; } }));
console.log('done,', bad, 'failed');
