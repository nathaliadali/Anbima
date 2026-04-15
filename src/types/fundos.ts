// Tipos de dados consumidos pelo frontend
// Correspondem à estrutura dos JSONs gerados pelo pipeline Python

export interface DadoAnual {
  periodo: string;          // "YYYY-MM" (dezembro do ano de referência)
  ano: number;
  renda_fixa?: number | null;
  renda_fixa_sem_credito?: number | null;
  renda_fixa_com_credito?: number | null;
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
  renda_fixa:   "#1B3157", // Azul Profundidade 1
  multimercado: "#5FBB47", // Verde Vanguarda
  acoes:        "#F58C2E", // Laranja Vanguarda
  cambial:      "#963B82", // Roxo Vanguarda
  previdencia:  "#FFC24F", // Amarelo Vanguarda
  etf:          "#2E96BF", // Azul Profundidade 3
  fidc:         "#0D6696", // Azul Profundidade 2
  fip:          "#00BADB", // Azul Profundidade 4
  fiagro:       "#F04F6E", // Rosa Vanguarda
  fii:          "#6B7280", // Cinza neutro
  offshore:     "#94A3B8", // Cinza-azulado neutro
};
