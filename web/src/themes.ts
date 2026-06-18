import { PieceType } from "./pieces";

export type Theme = Record<PieceType, string>;

export const PIECE_LABELS: Record<PieceType, string> = {
  [PieceType.LargeTriangle]: "Large triangle",
  [PieceType.MediumTriangle]: "Medium triangle",
  [PieceType.SmallTriangle]: "Small triangle",
  [PieceType.Square]: "Square",
  [PieceType.Parallelogram]: "Parallelogram",
};

interface ThemeGroup {
  label: string;
  themes: Record<string, Theme>;
}

function theme(large: string, medium: string, small: string, square: string, para: string): Theme {
  return {
    [PieceType.LargeTriangle]: large,
    [PieceType.MediumTriangle]: medium,
    [PieceType.SmallTriangle]: small,
    [PieceType.Square]: square,
    [PieceType.Parallelogram]: para,
  };
}

export const THEME_GROUPS: ThemeGroup[] = [
  {
    label: "Classics",
    themes: {
      classic: theme("#e74c3c", "#f1c40f", "#3498db", "#2ecc71", "#9b59b6"),
      pastel: theme("#ffb3ba", "#ffe0ba", "#bae1ff", "#baffc9", "#d7baff"),
      mono: theme("#2b2b2b", "#5c5c5c", "#8c8c8c", "#b3b3b3", "#444444"),
    },
  },
  {
    label: "Designer",
    themes: {
      // Bauhaus / De Stijl primaries: red, yellow, blue, near-black, warm cream.
      bauhaus: theme("#d32f2f", "#fbc02d", "#1565c0", "#212121", "#e8dfca"),
      // Nord "aurora" accents (Arctic Ice Studio).
      nord: theme("#bf616a", "#d08770", "#ebcb8b", "#a3be8c", "#b48ead"),
      // Dracula theme accent colors.
      dracula: theme("#ff5555", "#ffb86c", "#f1fa8c", "#50fa7b", "#bd93f9"),
      // Solarized accent colors (Ethan Schoonover).
      solarized: theme("#dc322f", "#cb4b16", "#b58900", "#859900", "#268bd2"),
      // 1980s Memphis Group: bright, postmodern, playful.
      memphis: theme("#f6416c", "#f8aa4b", "#ffde7d", "#00b8a9", "#9d65c9"),
      // Muted earth tones / terracotta interior palette.
      terracotta: theme("#c1666b", "#d9a05b", "#e3c16f", "#8a9b68", "#8b5e3c"),
    },
  },
];

export const THEMES: Record<string, Theme> = Object.fromEntries(
  THEME_GROUPS.flatMap((group) => Object.entries(group.themes)),
);

export const DEFAULT_THEME = "classic";
export const DEFAULT_SILHOUETTE_COLOR = "#1a1a1a";
