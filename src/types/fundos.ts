// Tipos de dados consumidos pelo frontend
// Correspondem à estrutura dos JSONs gerados pelo pipeline Python

export interface DadoAnual {
  periodo: string;          // "YYYY-MM" (dezembro do ano de referência)
  ano: number;
  renda_fixa?: number | null;
  acoes?: number | null;
  multimercado?: number | null;
  cambial?: number | null;
  previdencia?: number | null;
  etf?: number | null;
  fidc?: number | null;
  fip?: number | null;
  fiagro?: number | null;
  fii?: number | null;
  offshore?: number | null;
  total?: number | null;
}

export interface DadoMensalResumo {
  periodo: string;          // "YYYY-MM"
  [chave: string]: number | string | null;
}

export interface Subcategoria {
  nome: string;
  codigo: string | null;
  valores: Record<string, number | null>;
}

export interface ClasseFundo {
  nome: string;
  chave: string;
  aberta: boolean;          // true = exibe subcategorias
  valores: Record<string, number | null>;  // chave = "YYYY-MM"
  subcategorias: Subcategoria[];
}

export interface TabelaDetalhada {
  meses: string[];          // ["2025-06", "2025-07", ...]
  classes: ClasseFundo[];
}

export interface Meta {
  ultima_atualizacao: string;
  ultimo_mes_disponivel: string | null;
  ultimo_ano_disponivel: number | null;
  arquivos_processados: string[];
  n_meses_disponiveis: number;
}

// Constantes de display
export const CLASSE_LABELS: Record<string, string> = {
  renda_fixa: "Renda Fixa",
  acoes: "Ações",
  multimercado: "Multimercado",
  cambial: "Cambial",
  previdencia: "Previdência",
  etf: "ETF",
  fidc: "FIDC",
  fip: "FIP",
  fiagro: "FIAGRO",
  fii: "FII",
  offshore: "Off-shore",
};

export const ORDEM_CLASSES: (keyof Omit<DadoAnual, "periodo" | "ano" | "total">)[] = [
  "renda_fixa",
  "multimercado",
  "acoes",
  "cambial",
  "previdencia",
  "etf",
  "fidc",
  "fip",
  "fiagro",
  "fii",
  "offshore",
];

export const CORES_CLASSES: Record<string, string> = {
  renda_fixa: "#003DA5",
  multimercado: "#00843D",
  acoes: "#E85C0D",
  cambial: "#7B2D8B",
  previdencia: "#C4920A",
  etf: "#0087CC",
  fidc: "#555B6E",
  fip: "#89B0AE",
  fiagro: "#57A06C",
  fii: "#D4A373",
  offshore: "#9B5DE5",
};
