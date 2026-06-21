import "./style.css";
import { Z2 } from "./algebra";
import { Point } from "./geometry";
import { loadIndex, loadTangram, tangramToJson } from "./io";
import type { IndexEntry } from "./io";
import { PiecePlacement, Tangram } from "./model";
import { PieceType } from "./pieces";
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
          <div id="shape-list" class="button-list"></div>
        </section>
        <section>
          <h2>Theme</h2>
          <select id="theme-select">
            ${THEME_GROUPS.map(
              (group) => `
                <optgroup label="${group.label}">
                  ${Object.keys(group.themes)
                    .map((name) => `<option value="${name}">${capitalize(name)}</option>`)
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
const silhouetteColorInput = document.getElementById("silhouette-color") as HTMLInputElement;
const roundingSlider = document.getElementById("rounding-slider") as HTMLInputElement;
const roundingValue = document.getElementById("rounding-value")!;
const downloadBtn = document.getElementById("download-btn")!;
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

function buildShapeList(): void {
  const q = state.shapeQuery.toLowerCase().trim();
  let filtered = state.figures;
  if (state.shapeCategory !== "all") filtered = filtered.filter((f) => f.category === state.shapeCategory);
  if (q) filtered = filtered.filter((f) => (f.title ?? labelFor(f.file)).toLowerCase().includes(q));

  const showHeaders = state.shapeCategory === "all" && !q;

  // Deduplicate titles within the visible set
  const titleCount = new Map<string, number>();
  for (const e of filtered) {
    const t = e.title ?? labelFor(e.file);
    titleCount.set(t, (titleCount.get(t) ?? 0) + 1);
  }
  const titleSeen = new Map<string, number>();
  function entryLabel(e: IndexEntry): string {
    const base = e.title ?? labelFor(e.file);
    const n = titleSeen.get(base) ?? 0;
    titleSeen.set(base, n + 1);
    return titleCount.get(base)! > 1 ? `${base} ${n + 1}` : base;
  }

  if (showHeaders) {
    const byCategory = new Map<string, IndexEntry[]>();
    for (const e of filtered) {
      const list = byCategory.get(e.category) ?? [];
      list.push(e);
      byCategory.set(e.category, list);
    }
    shapeListEl.innerHTML = [...byCategory.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([cat, entries]) => {
        const sorted = [...entries].sort((a, b) =>
          (a.title ?? labelFor(a.file)).localeCompare(b.title ?? labelFor(b.file)),
        );
        return `<div class="shape-category">${capitalize(cat)}</div>
          ${sorted.map((e) => `<button data-file="${e.file}" class="${e.file === state.exampleFile ? "active" : ""}">${entryLabel(e)}</button>`).join("")}`;
      })
      .join("");
  } else {
    const sorted = [...filtered].sort((a, b) =>
      (a.title ?? labelFor(a.file)).localeCompare(b.title ?? labelFor(b.file)),
    );
    if (sorted.length === 0) {
      shapeListEl.innerHTML = `<div class="shape-empty">No shapes found</div>`;
    } else {
      shapeListEl.innerHTML = sorted
        .map((e) => `<button data-file="${e.file}" class="${e.file === state.exampleFile ? "active" : ""}">${entryLabel(e)}</button>`)
        .join("");
    }
  }

  shapeListEl.querySelectorAll<HTMLButtonElement>("button[data-file]").forEach((btn) => {
    btn.addEventListener("click", () => loadExample(btn.dataset.file!));
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

async function loadExample(file: string): Promise<void> {
  state.tangram = await loadTangram(`/examples/${file}`);
  state.exampleFile = file;
  state.selectedIndex = null;
  buildShapeList();
  render();
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
