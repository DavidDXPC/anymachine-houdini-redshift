// Summarise check.json + verify_glb.json for all bags into a markdown table (stdout).
import { readFileSync } from 'node:fs';
const B = 'C:/Users/apek-anna/Developer/anymachine/backpacks/out/';
for (const bag of ['rucksack', 'daypack', 'rolltop']) {
  const r = JSON.parse(readFileSync(B + bag + '/check.json'));
  const v = JSON.parse(readFileSync(B + bag + '/verify_glb.json'));
  const sw = {}, pr = {};
  for (const row of r.rows) {
    const tgt = row.tag.startsWith('sweep') ? sw : pr;
    const key = row.tag.split(':')[1];
    for (const [p, m] of Object.entries(row.parts)) {
      if (p === '_self') { for (const [o, n] of Object.entries(m)) { const k = key + '|self:' + o; tgt[k] = Math.max(tgt[k] || 0, n); } continue; }
      const k = key + '|' + p; tgt[k] = Math.max(tgt[k] || 0, m.max_pen_mm);
      if ('min_z_mm' in m) { const kz = key + '|' + p + ' min z'; tgt[kz] = Math.min(tgt[kz] ?? 1e9, m.min_z_mm); }
    }
  }
  console.log(`\n### ${bag}: ${r.states} states, clamp max dev ${Math.max(...Object.values(r.clamp_max_dev_mm))} mm, GLB ${v.size_kb} KB, actions ${v.actions.join(', ')}, demo pose match median ${v.pose_match['demo@60'].median_mm} mm`);
  console.log('\n| sweep (others at default) | worst part: max penetration mm |\n|---|---|');
  const byc = {};
  for (const [k, val] of Object.entries(sw)) { const [c, p] = k.split('|'); (byc[c] ||= []).push(`${p} ${typeof val === 'number' ? val.toFixed(1) : val}`); }
  for (const [c, l] of Object.entries(byc)) console.log(`| ${c} | ${l.join('; ')} |`);
  console.log('\n| coupled pair (5x5) | worst |\n|---|---|');
  const byp = {};
  for (const [k, val] of Object.entries(pr)) { const [c, p] = k.split('|'); (byp[c] ||= []).push([p, val]); }
  for (const [c, l] of Object.entries(byp)) console.log(`| ${c} | ${l.filter(([p, x]) => (p.includes('min z') ? x < 0 : x > 4)).map(([p, x]) => `${p} ${x.toFixed(1)}`).join('; ') || 'all <= 4 mm'} |`);
}
