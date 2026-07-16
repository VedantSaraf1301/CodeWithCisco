// Both helpers derive purely from the live incident feed already in
// context -- no separate backend endpoint needed, and the numbers always
// agree with what the Incident Feed and stat tiles show.

export function ratchetTimeline(feed) {
  const real = feed
    .filter((e) => !e.chaos && !e.audit_demo)
    .slice()
    .reverse(); // feed is newest-first; charts read left-to-right in time
  let hits = 0;
  return real.map((e, i) => {
    if (e.fabric_hit) hits += 1;
    const index = i + 1;
    return { index, pct: Math.round((hits / index) * 100) };
  });
}

export function resolutionPathCounts(feed) {
  const real = feed.filter((e) => !e.chaos && !e.audit_demo);
  const counts = { cached: 0, layer1: 0, layer2: 0, layer3: 0 };
  for (const e of real) {
    if (e.fabric_hit) {
      counts.cached += 1;
      continue;
    }
    const layer = e.result?.layer_used;
    if (layer === 1) counts.layer1 += 1;
    else if (layer === 2) counts.layer2 += 1;
    else if (layer === 3) counts.layer3 += 1;
  }
  return counts;
}
