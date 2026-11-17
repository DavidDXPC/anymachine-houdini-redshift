// Extra close-up sheets for the complicated parts of the equipment family (same form as kit/gen_closeups.mjs, which
// has a fixed table for the landmarks): six named close-ups, the piece's own turnaround sheet as the input image.
//   FAL_KEY=<your key> node rig2_blender/kit/equipment/gen_close.mjs [--force] [id ...]
// Output: rig2_blender/kit/sheets/<id>_close1.png. FAL_KEY from the environment, never printed. About $0.25 a sheet.
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url)), TOOL = path.join(HERE, '..', '..', '..', 'tools', 'detail_fal.mjs'), OUT = path.join(HERE, '..', 'sheets');
const CLOSE = {
  xmas_tree: { what: 'a wellhead christmas tree (valve tree) painted muted green with red handwheels, on a yellow kerb with grating',
    sheets: [['one master gate valve seen square-on from the front: the forged block body, the bonnet with its stud ring, the stem and the red handwheel with its spokes', 'the same master valve from the side, showing how far the bonnet and handwheel stand off the bore and the flange above and below', 'the cross block where the two wing arms leave the vertical bore, with the studded flanges', 'a wing valve and the choke at the end of the wing arm: choke body, its adjusting stem and indicator, the blind end flange', 'the tree cap on top: cap flange, needle valve and the pressure gauge', 'the wellhead flange at the bottom where it passes through the grating in the kerb, with its ring of studs and nuts']] },
  hpu: { what: 'a hydraulic power unit: a blue steel oil tank in a drip tray with a motor and pump, accumulator bottles, filters, a valve block and hose reels',
    sheets: [['the electric motor on top of the tank from the side: finned body, fan cowl, terminal box, feet on the mounting plate', 'the bellhousing and the hydraulic pump coupled to the motor, with the suction and pressure lines leaving it', 'the row of four black accumulator bottles: the clamps and bracket holding them, the gas valve caps on top, the manifold under them', 'the valve block with its solenoids, levers and the small steel pipes with compression fittings', 'the two filter housings with their bowls and the clogging indicator, and the level sight glass on the tank side', 'one hose reel on the tank end: red side discs, black hose, swivel, bracket']] },
  tugger_winch: { what: 'an orange air tugger winch with a yellow mesh guard over its drum, an air motor and levers, on a base frame bolted to the deck',
    sheets: [['the drum with the guard removed, seen square-on: drum barrel, the two flanges, the wire rope wound in neat layers and its anchor', 'one side frame from the end: the ribbed cast plate, bearing cover with its bolt circle, grease nipple', 'the yellow guard: frame, mesh, hinges and how it bolts to the side frames', 'the air motor and gearbox on the side with the air inlet pipe, valve and exhaust silencer', 'the brake lever and the control lever: pivots, linkage, black knobs, the brake band', 'a corner of the base frame with its hold-down bolt, washer plate and the weld to the side frame']] },
  chem_skid: { what: 'a chemical injection skid: two stainless tote tanks in a blue steel frame on a blue bunded base, two dosing pumps, stainless tubing and a control box at one end',
    sheets: [['the pump end seen square-on from the front: the two dosing pumps with their motors on plinths, suction and discharge tubing, valves, pulsation dampener, pressure gauge', 'one dosing pump from the side at close range: motor with cooling fins, gearbox, diaphragm pump head with its bolts, the tube fittings', 'the stainless control box on the frame with its hinges, latch, cable glands underneath and conduit', 'a tote tank front seen square-on: pressed panel, the outlet ball valve at the bottom, a level gauge tube, a blank label plate and a blank hazard diamond', 'the top of a tank: bolted manway lid, vent, filler cap, and the tubing manifold running across to the pumps', 'a corner of the blue bund base with a fork pocket, the frame post standing on it and a lifting lug at the top corner of the frame']] },
  air_receiver: { what: 'a vertical air receiver pressure vessel painted light grey, on legs, with a bolted manway, flanged nozzles, a relief valve and a pressure gauge',
    sheets: [['the bolted manway seen square-on: cover, ring of bolts, two handles and the hinge or davit arm', 'the same manway from the side, showing how far the neck and cover stand off the shell and the davit', 'the top head with the relief valve on its nozzle and the pressure gauge with its isolating valve and syphon tube', 'a side nozzle with its weld-neck flange, studs and nuts and the reinforcing pad on the shell', 'the nameplate on its stand-off bracket and the girth weld seam of the shell beside it', 'the bottom of the vessel: the dished head, drain valve, and a leg with its base plate and anchor bolts']] },
  control_station: { what: 'a local control station: a stainless steel cabinet with a window and push buttons on a grey steel stand with a sloping sunshade',
    sheets: [['the cabinet door seen square-on: window with its gasket, the row of push buttons and indicator lamps, the emergency stop, the handle', 'the hinge side of the door: two lift-off hinges and the door edge with its gasket lip', 'the latch side: quarter-turn latches and the handle', 'the underside of the cabinet: the row of cable glands and the steel conduits dropping down the stand, with their saddle clamps', 'the sunshade from below and the side: the folded plate, its two brackets and the bolts to the stand', 'the foot of the stand: base plate, gussets and anchor bolts, and the conduits entering the deck']] },
  heat_exchanger: { what: 'a horizontal shell-and-tube heat exchanger on two saddles, with ribbed aluminium insulation cladding, a flat bolted channel cover at one end and a dished bonnet at the other',
    sheets: [['the channel head with its flat cover seen from the end: the stud circle, the cover thickness, lifting lug', 'the same channel end from the side: channel barrel, the girth flanges, studs and nuts, the gap to the cladding', 'the dished bonnet end from the side: bonnet, girth flange pair with studs, where the cladding stops', 'a top nozzle rising through the cladding: collar flashing, the nozzle neck and its flange with studs', 'a saddle: wear plate under the shell, web, ribs, base plate and anchor bolts', 'the ribbed cladding with a banding strap and its buckle, an overlap seam with rivets, and the nameplate bracket']] },
};
const PROMPT = (what, six) => `A reference sheet of close-up photographs of ONE piece of equipment, for a 3D modeller who must build it accurately: ${what}. The input image shows this exact object from six directions; every close-up must show that same object, with the same colours, the same construction and the same condition.

Layout: six close-up photographs in a tidy grid of three columns and two rows, with clear space between them, each on a plain light-grey background or with the rest of the object softly behind. In reading order:
${six.map((s, i) => `(${i + 1}) ${s};`).join('\n')}

Each close-up is photographed square-on or at a slight angle from about a metre away, so the shape, the sections used, the joints and the fastener pattern are completely clear and could be measured. No people. Real industrial equipment at real proportions: correct fastener sizes, weld seams, cast and forged surfaces, bolted flanges. Photographic, soft even overcast light, very sharp, true-to-life materials. Condition: in daily use on a North Sea platform and somewhat dirty but maintained: dark grime runs below fittings, grease near moving parts, paint chipped to primer on edges, a little rust bleed at joints, no heavy rust.

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
  p.on('close', (c) => {
    fs.appendFileSync(path.join(HERE, 'spend.jsonl'), JSON.stringify({ time: new Date().toISOString(), id: `${j.id}_close${j.i + 1}`, ok: c === 0, est_usd: 0.25 }) + '\n');
    console.log(`${j.id}_close${j.i + 1}: ${c === 0 ? 'ok' : 'FAILED ' + log.trim().slice(0, 200)}`); done();
  });
});
await Promise.all(jobs.map(run));
