// Extra close-up reference sheets for the large structures (crane, derrick, flare boom, separator tower, helideck):
// each sheet is six named close-ups of the exterior, so the modeller can build the parts accurately. The object's own
// turnaround sheet is the input image, so the close-ups show the same object.
//   node rig2_blender/kit/gen_closeups.mjs [--force] [id ...]
// Output: rig2_blender/kit/sheets/<id>_close1.png, _close2.png, ... FAL_KEY from the environment, never printed.
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url)), TOOL = path.join(HERE, '..', '..', 'tools', 'detail_fal.mjs'), OUT = path.join(HERE, 'sheets');
const CLOSE = {
  crane: {
    what: 'an offshore pedestal crane with a yellow lattice boom and a red operator cab',
    sheets: [
      ['the boom foot: the two pivot pins and brackets where the lattice boom hinges on the crane house', 'one bay of the lattice boom seen square-on from the side: two chords, the diagonal lacing and how each lacing tube is welded to the chord', 'the same boom bay seen from above, showing the top face lacing pattern and the boom width', 'the boom tip: sheave block, wire ropes and the tip frame', 'the hook block with its sheaves, side plates and hook, hanging on wire rope', 'a bolted splice joint between two boom sections, with flange plates and bolts'],
      ['the operator cab from outside: windows, door, handrail and wiper, no interior', 'the crane house side: machinery housing panels, louvres, access door and ladder', 'the slew ring and the top of the pedestal: bolted ring, grease lines, the pedestal tube', 'the A-frame or gantry on top of the crane house with the boom hoist rope sheaves', 'the pedestal base where the tube meets the deck: stiffener gussets and the weld', 'the walkway and handrail round the crane house with its grating floor'],
    ],
  },
  derrick: {
    what: 'a red and white steel lattice drilling derrick on a substructure',
    sheets: [
      ['one corner leg of the derrick at a horizontal girt: the leg section, the gusset plate and how girt and diagonal braces bolt to it', 'one full face panel of the derrick seen square-on: two legs, a horizontal girt above and below and the cross bracing between', 'the place where the paint changes from red to white on a leg, with a bolted leg splice', 'the crown at the top: crown block sheaves, the water table platform with handrail, aviation light', 'the ladder with safety cage running up one face, and a small rest platform', 'the racking platform halfway up, cantilevered inside the derrick, seen from outside'],
      ['the derrick foot: base plate, anchor bolts and the shoe where a leg lands on the drill floor', 'the substructure under the drill floor seen from the side: heavy box girders, cross bracing and columns', 'a corner of the substructure where a column meets a girder: stiffeners, bolted flange', 'the V-door opening in one face of the derrick at drill floor level with the pipe ramp', 'the wind wall cladding panels round the drill floor, from outside', 'the stair from the deck up to the drill floor with handrails'],
    ],
  },
  flare_boom: {
    what: 'a red and white triangular steel lattice flare boom reaching out over the sea from the edge of an offshore platform',
    sheets: [
      ['the boom root: the pinned connections and brackets where the three chords meet the platform edge', 'one bay of the triangular lattice seen square-on from the side: top chord, bottom chord, diagonals and the welded tube joints', 'the cross-section of the boom seen end-on: three chords in a triangle with the walkway and the flare gas pipe inside', 'the walkway along the boom: grating, handrail and how it hangs from the lattice', 'the flare tip: burner stack, heat shield and pilot lines at the end of the boom', 'the flare gas pipe on its supports along the boom, with a flanged joint'],
    ],
  },
  separator_tower: {
    what: 'a tall process tower on an offshore platform: an open steel frame holding stacked pressure vessels, with access platforms and ladders',
    sheets: [
      ['a frame corner at a platform level: column, beam, bolted connection and bracing gusset', 'one access platform from outside: grating floor, handrail, toe board and its support brackets', 'a caged ladder between two platform levels', 'a vessel saddle or support ring where a vessel sits in the frame', 'a nozzle on a vessel with its flange, bolts and the pipe leaving it', 'the base of the tower where the columns land on the deck: base plates and anchor bolts'],
    ],
  },
  helideck: {
    what: 'an offshore platform helideck: a dark green landing deck with white and yellow markings',
    sheets: [
      ['the perimeter safety net: the steel outrigger frame sloping outward and the net panel lashed to it', 'the deck edge: kerb, drain gutter and a green perimeter light', 'the deck surface up close: textured green coating, the edge of a white painted marking, a tie-down point set in the deck', 'the support truss under the helideck edge where it cantilevers from the building', 'the access stair landing where it meets the helideck, with a foam monitor on a post', 'the windsock mast base and a floodlight on the deck edge'],
    ],
  },
};
const PROMPT = (what, six) => `A reference sheet of close-up photographs of the exterior of ONE structure, for a 3D modeller who must build it accurately: ${what}. The input image shows this exact structure from six directions; every close-up must show that same structure, with the same colours, the same construction and the same condition.

Layout: six close-up photographs in a tidy grid of three columns and two rows, with clear space between them, each on a plain light-grey background or with the rest of the structure softly behind. In reading order:
${six.map((s, i) => `(${i + 1}) ${s};`).join('\n')}

Each close-up is photographed square-on or at a slight angle from a few metres away, so the shape, the sections used (tube, angle, I-beam, plate), the joint and the fastener pattern are completely clear and could be measured. Exterior only: no interiors, no people. Real industrial steelwork at real proportions: correct member sizes, weld seams, gusset plates, bolted flanges. Photographic, soft even overcast light, very sharp, true-to-life materials. Condition: maintained and repainted within the last few years, light honest wear only: paint chipped to primer at edges, a few small rust blooms at welds and bolts, no heavy rust, no grime.

No text, no labels, no arrows, no logos, no brand names, no watermark, no borders.`;
const args = process.argv.slice(2); const force = args.includes('--force'), want = args.filter((a) => a !== '--force');
const jobs = [];
for (const [id, c] of Object.entries(CLOSE)) {
  if (want.length && !want.includes(id)) continue;
  c.sheets.forEach((six, i) => { const out = path.join(OUT, `${id}_close${i + 1}.png`); if (force || !fs.existsSync(out)) jobs.push({ id, i, out, prompt: PROMPT(c.what, six) }); });
}
fs.mkdirSync(path.join(OUT, 'prompts'), { recursive: true });
console.log(jobs.length, 'close-up sheets to make');
const run = (j) => new Promise((done) => {
  const pf = path.join(OUT, 'prompts', `${j.id}_close${j.i + 1}.txt`); fs.writeFileSync(pf, j.prompt);
  const p = spawn(process.execPath, [TOOL, j.out, pf, '--size', 'landscape_16_9', '--model', 'sunburst', path.join(OUT, j.id + '_turn.png')], { stdio: ['ignore', 'pipe', 'pipe'] });
  let log = ''; p.stdout.on('data', (d) => (log += d)); p.stderr.on('data', (d) => (log += d));
  p.on('close', (c) => { console.log(`${j.id}_close${j.i + 1}: ${c === 0 ? 'ok' : 'FAILED ' + log.trim().slice(0, 200)}`); done(); });
});
await Promise.all(jobs.map(run));
