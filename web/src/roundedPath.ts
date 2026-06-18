/**
 * Build an SVG path `d` string for a polygon with rounded corners.
 *
 * Each corner is replaced by a quadratic curve that cuts in from both
 * adjacent edges. The cut length is capped at half the shorter adjacent
 * edge, so corners on short edges never overlap each other even at
 * amount=1.
 */
export function roundedPolygonPath(points: [number, number][], amount: number): string {
  const n = points.length;
  if (n < 3 || amount <= 0) {
    return `M ${points.map((p) => p.join(",")).join(" L ")} Z`;
  }

  const dist = (a: [number, number], b: [number, number]): number => Math.hypot(a[0] - b[0], a[1] - b[1]);

  const pointTowards = (from: [number, number], to: [number, number], distance: number): [number, number] => {
    const d = dist(from, to);
    if (d === 0) return from;
    const t = distance / d;
    return [from[0] + (to[0] - from[0]) * t, from[1] + (to[1] - from[1]) * t];
  };

  const entries: [number, number][] = [];
  const exits: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    const curr = points[i];
    const prev = points[(i - 1 + n) % n];
    const next = points[(i + 1) % n];
    const cut = amount * 0.5 * Math.min(dist(curr, prev), dist(curr, next));
    entries[i] = pointTowards(curr, prev, cut);
    exits[i] = pointTowards(curr, next, cut);
  }

  let d = `M ${entries[0].join(",")} `;
  for (let i = 0; i < n; i++) {
    d += `Q ${points[i].join(",")} ${exits[i].join(",")} `;
    d += `L ${entries[(i + 1) % n].join(",")} `;
  }
  return d + "Z";
}
