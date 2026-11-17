// Generate a reference image through fal (GPT Image 2.6).  FAL_KEY comes from the environment and is never logged.
//   node detail_fal.mjs <out.png> <promptfile.txt> [--size WxH|preset] [--model flare|sunburst] [input1.png input2.png ...]
// With inputs -> edit endpoint, without -> text-to-image.  Saves the prompt next to the image as <out>.prompt.txt
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const out = args.shift();
const promptFile = args.shift();
let size = "landscape_16_9", model = "flare";
const inputs = [];
while (args.length) {
  const a = args.shift();
  if (a === "--size") size = args.shift();
  else if (a === "--model") model = args.shift();
  else inputs.push(a);
}
const key = process.env.FAL_KEY;
if (!key) { console.error("FAL_KEY not set"); process.exit(2); }
const prompt = fs.readFileSync(promptFile, "utf8").trim();
const m = /^(\d+)x(\d+)$/.exec(size);
const body = { prompt, quality: "high", image_size: m ? { width: +m[1], height: +m[2] } : size };
if (inputs.length) {
  body.image_urls = inputs.map((p) => "data:image/png;base64," + fs.readFileSync(p).toString("base64"));
}
const endpoint = `openai/gpt-image-2.6/${model}/${inputs.length ? "edit" : "text-to-image"}`;
const H = { Authorization: "Key " + key, "Content-Type": "application/json" };
const sub = await fetch("https://queue.fal.run/" + endpoint, { method: "POST", headers: H, body: JSON.stringify(body) });
const sj = await sub.json();
if (!sub.ok || !sj.request_id) { console.error("submit failed", sub.status, JSON.stringify(sj).slice(0, 600)); process.exit(1); }
const t0 = Date.now();
for (;;) {
  await new Promise((r) => setTimeout(r, 3000));
  const st = await (await fetch(sj.status_url, { headers: H })).json();
  if (st.status === "COMPLETED") break;
  if (st.status && !["IN_QUEUE", "IN_PROGRESS"].includes(st.status)) { console.error("status", JSON.stringify(st).slice(0, 600)); process.exit(1); }
  if (Date.now() - t0 > 15 * 60e3) { console.error("timeout"); process.exit(1); }
}
const res = await (await fetch(sj.response_url, { headers: H })).json();
const url = res?.images?.[0]?.url;
if (!url) { console.error("no image", JSON.stringify(res).slice(0, 800)); process.exit(1); }
const img = Buffer.from(await (await fetch(url)).arrayBuffer());
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, img);
fs.writeFileSync(out + ".prompt.txt", `endpoint: ${endpoint}\nimage_size: ${size}\nquality: high\ninputs: ${inputs.map((p) => path.basename(p)).join(", ")}\n\n${prompt}\n`);
console.log("saved", out, img.length, "bytes in", Math.round((Date.now() - t0) / 1000), "s");
