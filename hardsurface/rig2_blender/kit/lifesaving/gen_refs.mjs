// Reference sheets for the hand-modelled lifeboat station (replaces the generated `lifeboat` prop):
//   survival_craft  = the totally enclosed motor-propelled survival craft, on its own
//   lifeboat_davit  = fixed platform davit, winch, falls, embarkation platform (boat shown stowed in it)
// Same method as gen_sheets.mjs / gen_closeups.mjs: one turnaround each, then close-up sheets seeded from the turnaround.
//   FAL_KEY=<your key> node rig2_blender/kit/lifesaving/gen_refs.mjs [turn|close] [--force]
// Output: rig2_blender/kit/sheets/<id>_turn.png, <id>_close<n>.png.  Spend is appended to lifesaving/spend.jsonl (estimate).
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url)), TOOL = path.join(HERE, '..', '..', '..', 'tools', 'detail_fal.mjs'), OUT = path.join(HERE, '..', 'sheets');
const EST = 0.25;   // USD per high-quality 16:9 image, estimate
const LOOK = 'Condition: in working order on a modern North Sea platform, repainted within the last year: clean glossy marine paint, crisp edges, only the faintest salt dust and a few small scuffs. No rust, no grime, no dents.';
const NO = 'No people, no logos, no brand names, no watermark, no borders, no arrows, no dimension lines.';
const BOAT = `a totally enclosed motor-propelled survival craft (TEMPSC), the standard enclosed offshore lifeboat: about 7.5 m long, 2.7 m beam, 3 m high. International orange glass-fibre hull and canopy. Hull: a hard chine, a straight keel with a skeg, a fine raked bow, a transom stern; a heavy black rubber rubbing strake (fender) right round at the sheer line where hull and canopy join; a white becketed grab line hanging in loops along both sides just under the strake. Canopy: rounded enclosed superstructure with a large outward-opening boarding hatch on each side with two hinges and lever dog handles, a smaller hatch on top forward and one aft, a raised square conning position (steering tower) aft with small rectangular windows all round and a white navigation light on a short mast, small fixed rectangular portlights with black rubber gaskets, a stainless water-spray deluge pipe running along the top centre line with nozzles, grab rails along the canopy top. Lifting hooks: one heavy galvanised on-load release hook in a steel hook box forward and one aft on the centre line of the canopy. Stern: a bronze propeller inside a round steel nozzle guard with a rudder behind it, an exhaust outlet. Strips of silver retro-reflective tape in short bars round the canopy and along the hull; black stencilled capacity and identification lettering on the canopy sides (generic letters and numbers)`;
const DAVIT = `an offshore platform lifeboat station: a fixed twin-arm platform davit holding a stowed orange totally enclosed lifeboat outboard of the deck edge. Two welded white-painted steel box-section davit frames about 5 m apart, each a vertical column rising 3.5 m from a cantilever base girder at deck level with an arm reaching 2.5 m outboard at the top, a knee gusset at the elbow and a head sheave in cheek plates at the arm tip; a cross girder between the two columns carrying the blue electric lifeboat winch with twin grooved drums, gearbox, motor and a counterweighted brake lever; galvanised wire rope falls running from the winch drums over lead sheaves at the column heads, along the arms, over the head sheaves and down to a suspension block with a long link that hangs in each of the two lifting hooks of the boat. Below, a narrow embarkation platform of galvanised bar grating cantilevered from the deck edge on I-beam brackets with diagonal knee braces going down to a lower mounting pad, ochre-yellow tube handrails with toe boards on its ends and outboard edge and a gap with a safety chain opposite the side hatch of the boat; the boat held in against rubber fender pads by two wire gripe lashings with turnbuckles and slip hooks; a remote release wire and a small control box on one column`;
const TURN = (what) => `A technical reference sheet for 3D modelling, showing ONE object from six directions: ${what}.

Layout: six separate views of the same single object on a plain seamless light-grey background, arranged in a tidy grid of three columns and two rows with clear space between them. Top row: front elevation, left side elevation, back elevation. Bottom row: right side elevation, top plan view, three-quarter view from the front and slightly above. The five elevation and plan views are true orthographic projections with no perspective at all, drawn at the same scale; only the three-quarter view has perspective. Every view shows the identical object: same parts, same colours.

Photographic, not a drawing: a real object photographed for 3D scanning, soft even diffuse studio light, no cast shadows on the background, sharp focus edge to edge, true-to-life materials, real fasteners at real size. The whole object is inside each view with a margin. Nothing else in frame.

${LOOK}

${NO}`;
const CLOSE = (what, six) => `A reference sheet of close-up photographs of ONE object, for a 3D modeller who must build it accurately: ${what}. The input image shows this exact object from six directions; every close-up must show that same object, with the same colours, the same construction and the same condition.

Layout: six close-up photographs in a tidy grid of three columns and two rows, with clear space between them. In reading order:
${six.map((s, i) => `(${i + 1}) ${s};`).join('\n')}

Each close-up is photographed square-on or at a slight angle from one or two metres away, so the shape, the joint, the hardware and the fastener pattern are completely clear and could be measured. Exterior only. Real marine and industrial construction at real proportions. Photographic, soft even overcast light, very sharp, true-to-life materials.

${LOOK}

${NO}`;
const J = {
  turn: [
    ['survival_craft_turn', TURN(BOAT), null],
    ['lifeboat_davit_turn', TURN(DAVIT), null],
  ],
  close: [
    ['survival_craft_close1', CLOSE(BOAT, ['the side boarding hatch closed: its moulded coaming, two hinges, the lever dog handles, the rubber seal line and a grab handle', 'the forward lifting hook: the galvanised on-load release hook standing in its steel hook box on the canopy, with its bolted base plate and release cable', 'the conning position (steering tower): its small windows in black rubber gaskets, the navigation light and the top hatch', 'the stern from behind and slightly below: propeller in its round nozzle guard, the rudder, the skeg and the exhaust outlet', 'the rubbing strake along the side with the white grab line hanging in loops through its eyes, seen square-on', 'the canopy side with bars of silver retro-reflective tape and black stencilled lettering, and one fixed portlight']), 'survival_craft_turn'],
    ['survival_craft_close2', CLOSE(BOAT, ['the bow from the front and slightly below: the stem, the chine running aft and the keel line', 'the canopy top seen from above: the deluge spray pipe with a nozzle and its clips, a grab rail and the top hatch with its hinges', 'the hull bottom amidships from the side: the chine, the flat of the bottom and the keel with its metal shoe', 'a fixed portlight up close: black rubber gasket, clear pane, the moulded recess', 'the towing and painter fitting at the bow: bollard or release hook and a fairlead', 'the join between hull and canopy at the stern quarter: the strake end, a moulded seam, a drain scupper']), 'survival_craft_turn'],
    ['lifeboat_davit_close1', CLOSE(DAVIT, ['a davit arm tip: the head sheave between two cheek plates on its pin, the wire rope fall over it and a rope keeper', 'the lifeboat winch on the cross girder: twin grooved drums with wire rope, gearbox, electric motor, the brake lever with its counterweight', 'the suspension block and long link hanging on the fall, engaged in the lifting hook of the boat', 'the foot of a davit column: the base plate with its ring of bolts on the cantilever base girder, stiffener gussets and weld seams', 'the elbow of a davit frame where column meets arm: the knee gusset, the lead sheave and the box-section welds', 'a gripe lashing: the wire with its turnbuckle (bottle screw), slip hook and the deck eye plate it is shackled to']), 'lifeboat_davit_turn'],
    ['lifeboat_davit_close2', CLOSE(DAVIT, ['the embarkation platform from above at an angle: bar grating panels, the kick plate and the edge beam', 'the underside of the embarkation platform: I-beam cantilever bracket, the diagonal knee brace and its bolted mounting pads on the deck edge girder', 'the handrail gap opposite the boarding hatch with its safety chain and hook, and the rail posts bolted to the edge beam', 'a rubber fender pad on its steel bracket where the boat hull rests against the platform', 'the control box and the remote release wire with its small guide pulleys on a davit column', 'the cross girder end where it is bolted to a davit column: flange plate, bolts, a lifting lug']), 'lifeboat_davit_turn'],
  ],
};
const args = process.argv.slice(2); const force = args.includes('--force'); const which = args.find((a) => a === 'turn' || a === 'close');
const jobs = Object.entries(J).filter(([k]) => !which || k === which).flatMap(([, l]) => l).filter(([id]) => force || !fs.existsSync(path.join(OUT, id + '.png')));
fs.mkdirSync(path.join(OUT, 'prompts'), { recursive: true });
const run = ([id, prompt, input]) => new Promise((done) => {
  const pf = path.join(OUT, 'prompts', id + '.txt'); fs.writeFileSync(pf, prompt);
  const p = spawn(process.execPath, [TOOL, path.join(OUT, id + '.png'), pf, '--size', 'landscape_16_9', '--model', 'sunburst', ...(input ? [path.join(OUT, input + '.png')] : [])], { stdio: ['ignore', 'pipe', 'pipe'] });
  let log = ''; p.stdout.on('data', (d) => (log += d)); p.stderr.on('data', (d) => (log += d));
  p.on('close', (c) => {
    console.log(`${id}: ${c === 0 ? 'ok' : 'FAILED ' + log.trim().slice(0, 300)}`);
    fs.appendFileSync(path.join(HERE, 'spend.jsonl'), JSON.stringify({ time: new Date().toISOString(), id, ok: c === 0, est_usd: EST }) + '\n'); done();
  });
});
console.log(jobs.length, 'sheets to make');
await Promise.all(jobs.map(run));
