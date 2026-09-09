import "./style.css";
import { Z2 } from "./algebra";
import { Point } from "./geometry";
import { loadIndex, loadTangram, tangramToJson } from "./io";
import type { IndexEntry } from "./io";
import { PiecePlacement, Tangram } from "./model";
import { PieceType } from "./pieces";
import type { Card, CardRenderOptions } from "./pdf";
import { roundedPolygonPath } from "./roundedPath";
import { DEFAULT_SILHOUETTE_COLOR, DEFAULT_THEME, PIECE_LABELS, THEME_GROUPS, THEMES } from "./themes";
import type { Theme } from "./themes";

// Canvas box matches A-series paper ratio (1 : sqrt(2)), e.g. A5. Orientation
// flips to whichever fits each tangram's own bounding box better, but the box
// itself only ever takes one of these two fixed sizes -- so switching shapes
// never produces an arbitrary, jumpy resize.
const PAPER_RATIO = Math.SQRT2;
const BOX_LONG = 480;
const BOX_SHORT = Math.round(BOX_LONG / PAPER_RATIO);
const BOX_PADDING = 24;

const PIECE_TYPES = Object.values(PieceType);

type FillMode = "fill" | "outline";
type ViewMode = "solution" | "silhouette";

function labelFor(file: string): string {
  return file
    .replace(/\.json$/, "")
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

function capitalize(word: string): string {
  return word[0].toUpperCase() + word.slice(1);
}

function formatThemeName(name: string): string {
  return name
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

const state = {
  tangram: null as Tangram | null,
  figures: [] as IndexEntry[],
  exampleFile: "cat.json",
  selectedIndex: null as number | null,
  pieceColors: { ...THEMES[DEFAULT_THEME] } as Theme,
  themeName: DEFAULT_THEME,
  silhouetteColor: DEFAULT_SILHOUETTE_COLOR,
  fillMode: "fill" as FillMode,
  cornerRounding: 0, // 0 (sharp) to 1 (max rounding, capped per-corner)
  shapeCategory: "all",
  shapeQuery: "",
  sortBy: "name" as "name" | "difficulty",
  // Titles with more than one figure (e.g. "Cat") collapse into a single
  // group in the sidebar; this tracks which ones the user has expanded.
  expandedShapeGroups: new Set<string>(),
};

let dragStartScreen: [number, number] | null = null;
let dragStartAnchor: Point | null = null;
let transform = { scale: 1, offsetX: 0, offsetY: 0 };

const app = document.getElementById("app")!;
app.innerHTML = `
  <h1>Tangram Editor</h1>
  <div id="layout">
    <aside id="sidebar">
      <button id="sidebar-toggle" aria-label="Collapse sidebar">&laquo;</button>
      <div id="sidebar-content">
        <section>
          <h2>Shapes</h2>
          <input type="search" id="shape-search" placeholder="Search…" autocomplete="off" />
          <div id="category-pills"></div>
          <div class="toggle-group" id="sort-toggle">
            <button data-value="name" class="active">A–Z</button>
            <button data-value="difficulty">Difficulty</button>
          </div>
          <div id="shape-list" class="button-list"></div>
        </section>
        <section>
          <h2>Theme</h2>
          <select id="theme-select">
            ${THEME_GROUPS.map(
              (group) => `
                <optgroup label="${group.label}">
                  ${Object.keys(group.themes)
                    .map((name) => `<option value="${name}">${formatThemeName(name)}</option>`)
                    .join("")}
                </optgroup>
              `,
            ).join("")}
          </select>
        </section>
        <section>
          <h2>Colors</h2>
          <div id="color-list"></div>
        </section>
        <section>
          <h2>Render</h2>
          <div class="toggle-group" id="fill-toggle">
            <button data-value="fill" class="active">Fill</button>
            <button data-value="outline">Outline</button>
          </div>
          <div id="silhouette-color-row" class="color-row">
            <label for="silhouette-color">Silhouette color</label>
            <input type="color" id="silhouette-color" value="${DEFAULT_SILHOUETTE_COLOR}" />
          </div>
          <div class="slider-row">
            <label for="rounding-slider">Corner rounding</label>
            <input type="range" id="rounding-slider" min="0" max="100" value="0" />
            <span id="rounding-value">0%</span>
          </div>
        </section>
        <section>
          <h2>File</h2>
          <button id="download-btn">Download JSON</button>
          <button id="pdf-btn" title="Download a double-sided A5 puzzle card (silhouette front, solution back) ready to print, laminate and hole-punch">Download card PDF</button>
          <button id="pdf-all-btn" title="Download every currently-listed shape as duplex A5 cards in one PDF">Download all shown (PDF)</button>
          <label class="pdf-option"><input type="checkbox" id="gutter-toggle" checked /> Binding gutter (hole punch)</label>
        </section>
      </div>
    </aside>
    <main id="main">
      <div id="canvases">
        <div class="canvas-panel">
          <div class="panel-label">Solution</div>
          <div class="canvas-wrap"><svg id="canvas-solution"></svg></div>
        </div>
        <div class="canvas-panel">
          <div class="panel-label">Silhouette</div>
          <div class="canvas-wrap"><svg id="canvas-silhouette"></svg></div>
        </div>
      </div>
      <div id="status"></div>
      <div id="help">Click a piece to select it. Drag to move. R = rotate 45&deg;. F = flip (parallelogram only).</div>
      <div id="source-link"></div>
    </main>
  </div>
`;

const solutionSvg = document.getElementById("canvas-solution") as unknown as SVGSVGElement;
const silhouetteSvg = document.getElementById("canvas-silhouette") as unknown as SVGSVGElement;
const statusEl = document.getElementById("status")!;
const shapeSearchEl = document.getElementById("shape-search") as HTMLInputElement;
const categoryPillsEl = document.getElementById("category-pills")!;
const shapeListEl = document.getElementById("shape-list")!;
const colorListEl = document.getElementById("color-list")!;
const themeSelect = document.getElementById("theme-select") as HTMLSelectElement;
const fillToggle = document.getElementById("fill-toggle")!;
const sortToggle = document.getElementById("sort-toggle")!;
const silhouetteColorInput = document.getElementById("silhouette-color") as HTMLInputElement;
const roundingSlider = document.getElementById("rounding-slider") as HTMLInputElement;
const roundingValue = document.getElementById("rounding-value")!;
const sourceLinkEl = document.getElementById("source-link")!;
const downloadBtn = document.getElementById("download-btn")!;
const pdfBtn = document.getElementById("pdf-btn") as HTMLButtonElement;
const pdfAllBtn = document.getElementById("pdf-all-btn") as HTMLButtonElement;
const gutterToggle = document.getElementById("gutter-toggle") as HTMLInputElement;
const sidebar = document.getElementById("sidebar")!;
const sidebarToggle = document.getElementById("sidebar-toggle")!;

function buildCategoryPills(): void {
  const cats = [...new Set(state.figures.map((f) => f.category))].sort();
  categoryPillsEl.innerHTML = ["all", ...cats]
    .map(
      (cat) =>
        `<button class="cat-pill${state.shapeCategory === cat ? " active" : ""}" data-cat="${cat}">
          ${cat === "all" ? "All" : capitalize(cat)}
        </button>`,
    )
    .join("");
  categoryPillsEl.querySelectorAll<HTMLButtonElement>(".cat-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.shapeCategory = btn.dataset.cat!;
      buildCategoryPills();
      buildShapeList();
    });
  });
}

// The base square is the shape all seven pieces are cut from -- the canonical
// starting point -- so we pin it to the top of the list rather than burying it
// among the other geometric figures.
const SQUARE_FILE = "square.json";

// Compact 5-star rating shown on each shape row (filled = difficulty).
function shapeStars(difficulty: number | undefined): string {
  if (!difficulty) return "";
  const stars = "★".repeat(difficulty) + "☆".repeat(5 - difficulty);
  return `<span class="shape-stars" title="difficulty ${difficulty} of 5">${stars}</span>`;
}

function byName(a: IndexEntry, b: IndexEntry): number {
  return (a.title ?? labelFor(a.file)).localeCompare(b.title ?? labelFor(b.file));
}

function buildShapeList(): void {
  const q = state.shapeQuery.toLowerCase().trim();
  let filtered = state.figures;
  if (state.shapeCategory !== "all") filtered = filtered.filter((f) => f.category === state.shapeCategory);
  if (q) filtered = filtered.filter((f) => (f.title ?? labelFor(f.file)).toLowerCase().includes(q));

  // Pull the base square out so it can be featured at the very top.
  const squareEntry = filtered.find((f) => f.file === SQUARE_FILE);
  filtered = filtered.filter((f) => f.file !== SQUARE_FILE);
  const featuredHtml = squareEntry
    ? `<div class="shape-featured">
        <button data-file="${SQUARE_FILE}" class="featured-square${SQUARE_FILE === state.exampleFile ? " active" : ""}">◇ The Square</button>
        <div class="featured-note">the shape all 7 pieces come from</div>
      </div>`
    : "";

  // Category headers only make sense for the default A-Z browse; difficulty
  // sort and search both flatten the list.
  const showHeaders = state.shapeCategory === "all" && !q && state.sortBy === "name";

  // Grouping same-titled figures (e.g. eight "Cat" variants) under one
  // collapsible row only makes sense alongside alphabetical name order --
  // difficulty sort and search both need every matching figure visible flat.
  const groupingEnabled = !q && state.sortBy === "name";

  function entryButton(e: IndexEntry, label: string, indented = false): string {
    const active = e.file === state.exampleFile ? " active" : "";
    const cls = indented ? "shape-row shape-row-child" : "shape-row";
    const thumb = `<span class="shape-thumb">${e.thumb ?? ""}</span>`;
    return `<button data-file="${e.file}" class="${cls}${active}">${thumb}<span class="shape-name">${label}</span>${shapeStars(e.difficulty)}</button>`;
  }

  // Flat rendering (search / difficulty sort): every entry visible, with
  // "Title N" disambiguation when a title repeats in the visible set.
  function renderFlat(entries: IndexEntry[]): string {
    const titleCount = new Map<string, number>();
    for (const e of entries) {
      const t = e.title ?? labelFor(e.file);
      titleCount.set(t, (titleCount.get(t) ?? 0) + 1);
    }
    const titleSeen = new Map<string, number>();
    return entries
      .map((e) => {
        const base = e.title ?? labelFor(e.file);
        const n = titleSeen.get(base) ?? 0;
        titleSeen.set(base, n + 1);
        const label = titleCount.get(base)! > 1 ? `${base} ${n + 1}` : base;
        return entryButton(e, label);
      })
      .join("");
  }

  // Grouped rendering: consecutive same-titled entries (the list is already
  // name-sorted, so they're adjacent) collapse into one header row that
  // expands to show each variant. A group auto-expands while it contains the
  // active shape, via loadExample() adding its title to expandedShapeGroups.
  function renderGrouped(entries: IndexEntry[]): string {
    const groups: { title: string; items: IndexEntry[] }[] = [];
    for (const e of entries) {
      const t = e.title ?? labelFor(e.file);
      const last = groups[groups.length - 1];
      if (last && last.title === t) last.items.push(e);
      else groups.push({ title: t, items: [e] });
    }
    return groups
      .map((g) => {
        if (g.items.length === 1) return entryButton(g.items[0], g.title);
        const expanded = state.expandedShapeGroups.has(g.title);
        const hasActive = g.items.some((e) => e.file === state.exampleFile);
        const thumb = `<span class="shape-thumb">${g.items[0].thumb ?? ""}</span>`;
        const header = `<button type="button" class="shape-group-header${hasActive ? " active" : ""}" data-group="${g.title}">
          ${thumb}<span class="shape-name">${expanded ? "▾" : "▸"} ${g.title}</span>
          <span class="shape-group-count">${g.items.length}</span>
        </button>`;
        const children = expanded
          ? g.items.map((e, i) => entryButton(e, `${g.title} ${i + 1}`, true)).join("")
          : "";
        return header + children;
      })
      .join("");
  }

  function renderEntries(entries: IndexEntry[]): string {
    return groupingEnabled ? renderGrouped(entries) : renderFlat(entries);
  }

  if (showHeaders) {
    const byCategory = new Map<string, IndexEntry[]>();
    for (const e of filtered) {
      const list = byCategory.get(e.category) ?? [];
      list.push(e);
      byCategory.set(e.category, list);
    }
    shapeListEl.innerHTML = featuredHtml + [...byCategory.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([cat, entries]) => {
        const sorted = [...entries].sort(byName);
        return `<div class="shape-category">${capitalize(cat)}</div>
          ${renderEntries(sorted)}`;
      })
      .join("");
  } else {
    // Difficulty sort: easiest first, ties broken by name.
    const sorted = [...filtered].sort((a, b) =>
      state.sortBy === "difficulty"
        ? (a.difficulty ?? 0) - (b.difficulty ?? 0) || byName(a, b)
        : byName(a, b),
    );
    if (sorted.length === 0 && !featuredHtml) {
      shapeListEl.innerHTML = `<div class="shape-empty">No shapes found</div>`;
    } else {
      shapeListEl.innerHTML = featuredHtml + renderEntries(sorted);
    }
  }

  shapeListEl.querySelectorAll<HTMLButtonElement>("button[data-file]").forEach((btn) => {
    btn.addEventListener("click", () => loadExample(btn.dataset.file!));
  });
  shapeListEl.querySelectorAll<HTMLButtonElement>("button[data-group]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const title = btn.dataset.group!;
      if (state.expandedShapeGroups.has(title)) state.expandedShapeGroups.delete(title);
      else state.expandedShapeGroups.add(title);
      buildShapeList();
    });
  });
}

function buildColorList(): void {
  colorListEl.innerHTML = PIECE_TYPES.map(
    (type) => `
      <div class="color-row">
        <label for="color-${type}">${PIECE_LABELS[type]}</label>
        <input type="color" id="color-${type}" data-type="${type}" value="${state.pieceColors[type]}" />
      </div>
    `,
  ).join("");
  colorListEl.querySelectorAll<HTMLInputElement>("input[type=color]").forEach((input) => {
    input.addEventListener("input", () => {
      const type = input.dataset.type as PieceType;
      state.pieceColors[type] = input.value;
      render();
    });
  });
}

function setActiveToggle(group: HTMLElement, value: string): void {
  group.querySelectorAll<HTMLButtonElement>("button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.value === value);
  });
}

function toScreen(p: Point): [number, number] {
  const [x, y] = p.toFloat();
  return [x * transform.scale + transform.offsetX, y * transform.scale + transform.offsetY];
}

function pathFor(piece: PiecePlacement, rounding: number): string {
  const points = piece.vertices().map(toScreen);
  return roundedPolygonPath(points, rounding);
}

function styleFor(
  piece: PiecePlacement,
  isSelected: boolean,
  viewMode: ViewMode,
): { fill: string; stroke: string; width: number } {
  if (viewMode === "silhouette") {
    // Always a solid filled blob with no internal seams -- independent of
    // the solution panel's fill/outline toggle and corner rounding.
    return { fill: state.silhouetteColor, stroke: state.silhouetteColor, width: 0.5 };
  }
  const baseColor = state.pieceColors[piece.pieceType];
  if (state.fillMode === "fill") {
    return { fill: baseColor, stroke: isSelected ? "#000" : "#1a1a1a", width: isSelected ? 2.5 : 1 };
  }
  return { fill: "none", stroke: isSelected ? "#000" : baseColor, width: isSelected ? 5.5 : 4 };
}

function updateStatus(): void {
  if (!state.tangram) return;
  if (state.selectedIndex === null) {
    statusEl.textContent = "No piece selected.";
    return;
  }
  const p = state.tangram.pieces[state.selectedIndex];
  statusEl.textContent =
    `Selected: ${p.pieceType} #${p.pieceId}  ` +
    `anchor=(${p.anchor.x.toFloat().toFixed(2)}, ${p.anchor.y.toFloat().toFixed(2)})  ` +
    `orientation=${p.orientation * 45}deg  flipped=${p.flipped}`;
}

function drawPanel(svgEl: SVGSVGElement, viewMode: ViewMode, interactive: boolean, width: number, height: number): void {
  const tangram = state.tangram!;
  svgEl.setAttribute("width", String(width));
  svgEl.setAttribute("height", String(height));
  svgEl.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svgEl.innerHTML = "";

  const rounding = viewMode === "silhouette" ? 0 : state.cornerRounding;
  tangram.pieces.forEach((piece, index) => {
    const isSelected = interactive && index === state.selectedIndex;
    const style = styleFor(piece, isSelected, viewMode);
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathFor(piece, rounding));
    path.setAttribute("fill", style.fill);
    path.setAttribute("stroke", style.stroke);
    path.setAttribute("stroke-width", String(style.width));
    path.setAttribute("stroke-linejoin", "round");
    if (isSelected) path.classList.add("selected");
    if (interactive) path.addEventListener("pointerdown", (e) => onPointerDown(e, index));
    svgEl.appendChild(path);
  });
}

function render(): void {
  const tangram = state.tangram;
  if (!tangram) return;
  const [bx0, by0, bx1, by1] = tangram.boundingBox();
  const shapeWidth = bx1 - bx0;
  const shapeHeight = by1 - by0;

  const landscape = shapeWidth >= shapeHeight;
  const boxWidth = landscape ? BOX_LONG : BOX_SHORT;
  const boxHeight = landscape ? BOX_SHORT : BOX_LONG;

  const innerWidth = boxWidth - 2 * BOX_PADDING;
  const innerHeight = boxHeight - 2 * BOX_PADDING;
  const scale = Math.min(innerWidth / shapeWidth, innerHeight / shapeHeight);

  transform = {
    scale,
    offsetX: (boxWidth - shapeWidth * scale) / 2 - bx0 * scale,
    offsetY: (boxHeight - shapeHeight * scale) / 2 - by0 * scale,
  };

  drawPanel(solutionSvg, "solution", true, boxWidth, boxHeight);
  drawPanel(silhouetteSvg, "silhouette", false, boxWidth, boxHeight);

  updateStatus();
}

function onPointerDown(e: PointerEvent, index: number): void {
  state.selectedIndex = index;
  dragStartScreen = [e.clientX, e.clientY];
  dragStartAnchor = state.tangram!.pieces[index].anchor;
  (e.target as Element).setPointerCapture(e.pointerId);
  render();
}

function onPointerMove(e: PointerEvent): void {
  if (state.selectedIndex === null || dragStartScreen === null || dragStartAnchor === null) return;
  const dxScreen = e.clientX - dragStartScreen[0];
  const dyScreen = e.clientY - dragStartScreen[1];
  const dx = Math.round(dxScreen / transform.scale);
  const dy = Math.round(dyScreen / transform.scale);
  const newAnchor = dragStartAnchor.add(new Point(Z2.of(dx, 0), Z2.of(dy, 0)));
  state.tangram!.pieces[state.selectedIndex] = state.tangram!.pieces[state.selectedIndex].withAnchor(newAnchor);
  render();
}

function onPointerUp(): void {
  dragStartScreen = null;
  dragStartAnchor = null;
}

function onKeyDown(e: KeyboardEvent): void {
  if (state.selectedIndex === null || !state.tangram) return;
  if (e.key === "r" || e.key === "R") {
    state.tangram.pieces[state.selectedIndex] = state.tangram.pieces[state.selectedIndex].rotated(1);
    render();
  } else if (e.key === "f" || e.key === "F") {
    const piece = state.tangram.pieces[state.selectedIndex];
    if (piece.pieceType !== PieceType.Parallelogram) return;
    state.tangram.pieces[state.selectedIndex] = piece.flippedCopy();
    render();
  }
}

function downloadJson(): void {
  if (!state.tangram) return;
  const blob = new Blob([JSON.stringify(tangramToJson(state.tangram), null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${state.tangram.name}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function currentEntry(): IndexEntry | undefined {
  return state.figures.find((f) => f.file === state.exampleFile);
}

function pdfOptions(): CardRenderOptions {
  return {
    pieceColors: state.pieceColors,
    cornerRounding: state.cornerRounding,
    fillMode: state.fillMode,
    gutter: gutterToggle.checked,
  };
}

// The figures currently listed in the sidebar (same category/search filter and
// sort order), used for the "download all shown" batch export.
function filteredFigures(): IndexEntry[] {
  const q = state.shapeQuery.toLowerCase().trim();
  let f = state.figures;
  if (state.shapeCategory !== "all") f = f.filter((e) => e.category === state.shapeCategory);
  if (q) f = f.filter((e) => (e.title ?? labelFor(e.file)).toLowerCase().includes(q));
  return [...f].sort((a, b) =>
    state.sortBy === "difficulty" ? (a.difficulty ?? 0) - (b.difficulty ?? 0) || byName(a, b) : byName(a, b),
  );
}

function cardFromEntry(entry: IndexEntry, tangram: Tangram): Card {
  return {
    tangram,
    title: entry.title ?? labelFor(entry.file),
    category: entry.category,
    difficulty: entry.difficulty,
  };
}

async function downloadCurrentCardPdf(): Promise<void> {
  if (!state.tangram) return;
  const entry = currentEntry();
  const card: Card = entry
    ? cardFromEntry(entry, state.tangram)
    : { tangram: state.tangram, title: labelFor(state.exampleFile), category: "" };
  // jsPDF is heavy, so it's loaded on demand rather than in the initial bundle.
  const { downloadCardsPdf } = await import("./pdf");
  await downloadCardsPdf([card], pdfOptions(), `${state.tangram.name}-card.pdf`);
}

async function downloadAllShownPdf(): Promise<void> {
  const entries = filteredFigures();
  if (entries.length === 0) return;
  const original = pdfAllBtn.textContent;
  pdfAllBtn.disabled = true;
  pdfAllBtn.textContent = "Building…";
  try {
    const { downloadCardsPdf } = await import("./pdf");
    const cards = await Promise.all(
      entries.map(async (e) => cardFromEntry(e, await loadTangram(`/examples/${e.file}`))),
    );
    await downloadCardsPdf(cards, pdfOptions(), "tangram-cards.pdf");
  } finally {
    pdfAllBtn.disabled = false;
    pdfAllBtn.textContent = original;
  }
}

async function loadExample(file: string): Promise<void> {
  state.tangram = await loadTangram(`/examples/${file}`);
  state.exampleFile = file;
  state.selectedIndex = null;
  const entry = state.figures.find((f) => f.file === file);
  if (entry) state.expandedShapeGroups.add(entry.title ?? labelFor(entry.file));
  buildShapeList();
  render();
  const src = state.tangram.source;
  if (src && src.startsWith("http")) {
    sourceLinkEl.innerHTML = `<a href="${src}" target="_blank" rel="noopener">View source ↗</a>`;
  } else {
    sourceLinkEl.innerHTML = "";
  }
}

themeSelect.value = state.themeName;
themeSelect.addEventListener("change", () => {
  state.themeName = themeSelect.value;
  state.pieceColors = { ...THEMES[state.themeName] };
  buildColorList();
  render();
});

fillToggle.addEventListener("click", (e) => {
  const btn = (e.target as HTMLElement).closest("button");
  if (!btn) return;
  state.fillMode = btn.dataset.value as FillMode;
  setActiveToggle(fillToggle, state.fillMode);
  render();
});

sortToggle.addEventListener("click", (e) => {
  const btn = (e.target as HTMLElement).closest("button");
  if (!btn) return;
  state.sortBy = btn.dataset.value as "name" | "difficulty";
  setActiveToggle(sortToggle, state.sortBy);
  buildShapeList();
});

silhouetteColorInput.addEventListener("input", () => {
  state.silhouetteColor = silhouetteColorInput.value;
  render();
});

roundingSlider.addEventListener("input", () => {
  const percent = Number(roundingSlider.value);
  state.cornerRounding = percent / 100;
  roundingValue.textContent = `${percent}%`;
  render();
});

shapeSearchEl.addEventListener("input", () => {
  state.shapeQuery = shapeSearchEl.value;
  buildShapeList();
});

sidebarToggle.addEventListener("click", () => {
  const collapsed = sidebar.classList.toggle("collapsed");
  sidebarToggle.innerHTML = collapsed ? "&raquo;" : "&laquo;";
  sidebarToggle.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
});

downloadBtn.addEventListener("click", downloadJson);
pdfBtn.addEventListener("click", downloadCurrentCardPdf);
pdfAllBtn.addEventListener("click", downloadAllShownPdf);
solutionSvg.addEventListener("pointermove", onPointerMove);
solutionSvg.addEventListener("pointerup", onPointerUp);
window.addEventListener("keydown", onKeyDown);

async function init(): Promise<void> {
  state.figures = await loadIndex("/examples/index.json");
  buildColorList();
  buildCategoryPills();
  const hasCat = state.figures.some((f) => f.file === state.exampleFile);
  await loadExample(hasCat ? state.exampleFile : state.figures[0].file);
}

init();
