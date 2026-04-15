"""
parse_boletim.py
----------------
Le um arquivo Boletim.xlsx da ANBIMA e retorna DataFrames com:
  - pl_anual:         PL por classe, anual (Sheet "Pag. 4 - PL por Classe")
  - captacao_anual:   Captacao Liquida por classe, anual (Sheet "Pag. 8 - Cap. Liq. por Classe")
  - captacao_mensal_classe: Captacao mensal por classe (extraida do Sheet 8, linhas YYYYMM)
  - pl_mensal:        PL por tipo, mensal (Sheet "Pag. 5 - PL por Tipo")
  - captacao_mensal:  Captacao por tipo, mensal (Sheet "Pag. 9 - Cap. Liq. por Tipo")

Todos os valores de saida estao em R$ bilhoes (divididos por 1000, ja que o Excel usa R$ milhoes).

Estrutura dos sheets anuais (ex: Pag. 8 - Cap. Liq. por Classe):
  - Col A: periodo como float: ano (2006.0) ou YYYYMM (202501.0) ou NaN para footnotes
  - Col B: numero do periodo (ano ou mes)
  - Cols C+: valores por classe

Estrutura dos sheets mensais por tipo (ex: Pag. 9 - Cap. Liq. por Tipo):
  - Row 5: cabecalho com datas das colunas (datetime ou string "mar-26")
  - Col A: codigo do tipo (float) ou NaN para linhas de categoria
  - Col B: nome do tipo/categoria
  - Cols C+: valores mensais
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import re
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
COLUNAS_CLASSE_ANUAL = [
    "renda_fixa", "acoes", "multimercado", "cambial",
    "previdencia", "etf", "fidc", "fip", "fiagro", "fii", "offshore"
]

# Classes que ficam expandidas com subcategorias na tabela detalhada
CLASSES_ABERTAS = {"Renda Fixa", "Renda fixa", "Multimercados", "Multimercado", "Acoes", "Acoes"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_bilhoes(series: pd.Series) -> pd.Series:
    """Converte R$ milhoes -> R$ bilhoes, arredondando para 3 casas."""
    return (pd.to_numeric(series, errors="coerce") / 1000).round(3)


def _classify_periodo(val) -> tuple[str | None, str]:
    """
    Classifica um valor da coluna 'periodo' do Excel.
    Retorna (periodo_str, tipo) onde tipo e 'anual', 'mensal' ou 'invalido'.
    - val float 2006.0 -> ('2006', 'anual')
    - val float 202501.0 -> ('2025-01', 'mensal')
    - val datetime -> ('2006-12', 'anual' ou 'mensal')
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None, "invalido"

    # Datetime nativo (sheet PL por Classe)
    try:
        ts = pd.Timestamp(val)
        # Verifica se o Timestamp e valido e nao e o epoch (1970)
        if ts.year >= 1990:
            return ts.strftime("%Y-%m"), "mensal" if ts.month != 12 else "anual"
    except Exception:
        pass

    # Float/int representando ano ou YYYYMM
    if isinstance(val, (int, float)):
        n = int(val)
        # Ano simples: 1990-2100
        if 1990 <= n <= 2100:
            return str(n), "anual"
        # YYYYMM: 199001-210012
        ano = n // 100
        mes = n % 100
        if 1990 <= ano <= 2100 and 1 <= mes <= 12:
            return f"{ano:04d}-{mes:02d}", "mensal"

    # String
    if isinstance(val, str):
        val = val.strip()
        # Ano puro: "2006"
        if re.match(r"^\d{4}$", val) and 1990 <= int(val) <= 2100:
            return val, "anual"
        # "mar-26", "Jan/25", etc.
        m = re.match(
            r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*[-/](\d{2,4})",
            val, re.IGNORECASE
        )
        if m:
            meses = {
                "jan": "01", "fev": "02", "mar": "03", "abr": "04",
                "mai": "05", "jun": "06", "jul": "07", "ago": "08",
                "set": "09", "out": "10", "nov": "11", "dez": "12",
            }
            mes_num = meses[m.group(1).lower()[:3]]
            ano = m.group(2)
            if len(ano) == 2:
                ano = ("20" if int(ano) <= 50 else "19") + ano
            return f"{ano}-{mes_num}", "mensal"

    return None, "invalido"


def _parse_date_header(val) -> str | None:
    """Converte valor de cabecalho de coluna de mes para 'YYYY-MM'.
    Aceita qualquer periodo valido no formato YYYY-MM (incluindo dezembro)."""
    periodo, tipo = _classify_periodo(val)
    # Aceita apenas periodos no formato YYYY-MM (7 chars), nao apenas anos
    if periodo and len(periodo) == 7 and periodo[4] == "-":
        return periodo
    return None


# ---------------------------------------------------------------------------
# Parser: sheets com estrutura de LINHAS = periodos, COLUNAS = classes
# (Pag. 4 PL por Classe e Pag. 8 Cap. Liq. por Classe)
# ---------------------------------------------------------------------------
def _parse_classe_sheet(path: Path, sheet_name: str) -> dict[str, pd.DataFrame]:
    """
    Faz o parse de um sheet que mistura linhas anuais e mensais.

    Retorna dict com 'anual' e 'mensal'.
    - anual:  periodo=YYYY, colunas=classes
    - mensal: periodo=YYYY-MM, colunas=classes
    """
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)

    # Encontra linha de cabecalho (contem "Periodo" ou "Renda Fixa" nos valores)
    header_row = None
    for i, row in raw.iterrows():
        vals = [str(v).lower() for v in row if pd.notna(v) and str(v).strip()]
        joined = " ".join(vals)
        if ("periodo" in joined) or ("renda" in joined and "fixa" in joined):
            header_row = i
            break

    if header_row is None:
        raise ValueError(f"Cabecalho nao encontrado em {sheet_name}")

    data_start = header_row + 1
    df = raw.iloc[data_start:].copy()

    # Identifica nomes das colunas de classes (coluna B em diante)
    # O cabecalho esta espalhado em 2 linhas (rows header_row-1 e header_row)
    # mas geralmente as classes estao na linha header_row cols 2+
    header_vals = list(raw.iloc[header_row])
    # Tenta tambem a linha anterior para pegar os nomes das classes
    if header_row > 0:
        prev_vals = list(raw.iloc[header_row - 1])
    else:
        prev_vals = [None] * len(header_vals)

    # Monta lista de nomes de classes para as colunas 2+ (col C em diante)
    col_names = []
    for ci in range(2, len(header_vals)):
        name = header_vals[ci]
        if pd.isna(name) or str(name).strip() == "":
            name = prev_vals[ci] if ci < len(prev_vals) else None
        col_names.append(str(name).strip() if pd.notna(name) else None)

    rows_anual = []
    rows_mensal = []

    for _, row in df.iterrows():
        # Col A: identificador do periodo
        val_a = row.iloc[0]
        periodo_str, tipo = _classify_periodo(val_a)

        if tipo == "invalido":
            continue

        # Pula linhas que sao apenas texto de rodape (col B com texto longo)
        val_b = row.iloc[1] if len(row) > 1 else None
        if pd.notna(val_b) and isinstance(val_b, str) and len(val_b) > 20:
            continue

        # Extrai valores das colunas de classe (indice 2 em diante)
        row_dict = {"periodo": periodo_str}
        for ci, col_name in enumerate(col_names):
            val = row.iloc[ci + 2] if (ci + 2) < len(row) else None
            val_f = pd.to_numeric(val, errors="coerce")
            row_dict[f"col_{ci}"] = float(val_f) / 1000 if pd.notna(val_f) else None

        if tipo == "anual":
            rows_anual.append(row_dict)
        else:
            rows_mensal.append(row_dict)

    # Determina mapeamento col_0..col_N -> nomes de classe canonicos
    # Tenta mapear pelos nomes encontrados no cabecalho
    n_cols = len(col_names)
    canonical = _map_columns_to_canonical(col_names, n_cols)

    def to_df(rows):
        df_out = pd.DataFrame(rows)
        if df_out.empty:
            return df_out
        for ci, canon in canonical.items():
            src = f"col_{ci}"
            if src in df_out.columns:
                df_out[canon] = df_out[src].round(3)
                df_out.drop(columns=[src], inplace=True)
            else:
                # Remove col_N sem mapeamento
                pass
        # Remove col_N sem mapeamento que ainda restaram
        for c in [c for c in df_out.columns if c.startswith("col_")]:
            df_out.drop(columns=[c], inplace=True)
        # Extrai ano ou YYYY-MM para ordenacao
        df_out["periodo"] = df_out["periodo"].astype(str)
        return df_out

    anual_df = to_df(rows_anual)
    mensal_df = to_df(rows_mensal)

    # Para anual: adiciona coluna 'ano'
    if not anual_df.empty:
        anual_df["ano"] = anual_df["periodo"].str[:4].astype(int, errors="ignore")
        anual_df = anual_df.sort_values("ano").reset_index(drop=True)

    return {"anual": anual_df, "mensal": mensal_df}


def _map_columns_to_canonical(col_names: list, n_cols: int) -> dict[int, str]:
    """
    Mapeia indices de coluna para nomes canonicos (renda_fixa, acoes, etc.)
    baseado nos nomes encontrados no cabecalho.
    """
    mapping = {
        "renda fixa": "renda_fixa",
        "renda_fixa": "renda_fixa",
        "acoes": "acoes",
        "acoes": "acoes",
        "\u00e7\u00f5es": "acoes",  # ções
        "multimercados": "multimercado",
        "multimercado": "multimercado",
        "cambial": "cambial",
        "previd\u00eancia": "previdencia",
        "previdencia": "previdencia",
        "etf": "etf",
        "fidc": "fidc",
        "fip": "fip",
        "fiagro": "fiagro",
        "fii": "fii",
        "off shore": "offshore",
        "offshore": "offshore",
        "off-shore": "offshore",
        "total": "total",
    }

    result = {}
    used_canonicals = set()

    for ci, name in enumerate(col_names):
        if name is None:
            continue
        # Normaliza: remove acentos, lowercase
        name_norm = _normalize(name)
        # Tenta match exato
        for key, canon in mapping.items():
            if key in name_norm:
                if canon not in used_canonicals:
                    result[ci] = canon
                    used_canonicals.add(canon)
                    break

    return result


def _normalize(s: str) -> str:
    """Normaliza string: lowercase, remove acentos."""
    import unicodedata
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


# ---------------------------------------------------------------------------
# Parser: sheet PL por Classe (estrutura: datetime na col A)
# ---------------------------------------------------------------------------
def _parse_pl_classe(path: Path, sheet_name: str) -> pd.DataFrame:
    """
    Parse especifico para o sheet PL por Classe, onde col A e datetime.
    Retorna DataFrame anual.
    """
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)

    # Encontra linha de cabecalho
    header_row = None
    for i, row in raw.iterrows():
        vals = [str(v).lower() for v in row if pd.notna(v)]
        joined = " ".join(vals)
        if "renda" in joined and ("fixa" in joined or "fixo" in joined):
            header_row = i
            break

    if header_row is None:
        raise ValueError(f"Cabecalho nao encontrado em {sheet_name}")

    data_start = header_row + 1
    df = raw.iloc[data_start:].copy()

    col_names = []
    for ci in range(1, raw.shape[1]):
        name = raw.iloc[header_row, ci]
        if pd.isna(name) or str(name).strip() == "":
            name = raw.iloc[max(0, header_row - 1), ci] if header_row > 0 else None
        col_names.append(str(name).strip() if pd.notna(name) else None)

    canonical = _map_columns_to_canonical(col_names, len(col_names))

    rows = []
    for _, row in df.iterrows():
        val_a = row.iloc[0]
        periodo_str, tipo = _classify_periodo(val_a)
        if tipo == "invalido" or periodo_str is None:
            continue

        row_dict = {"periodo": periodo_str}
        for ci, canon in canonical.items():
            val = row.iloc[ci + 1] if (ci + 1) < len(row) else None
            val_f = pd.to_numeric(val, errors="coerce")
            row_dict[canon] = round(float(val_f) / 1000, 3) if pd.notna(val_f) else None

        rows.append(row_dict)

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    result["ano"] = result["periodo"].str[:4].astype(int)
    # Para PL, filtra apenas linhas com periodo = "YYYY-MM" (dezembro)
    # ou "YYYY" - pega apenas 1 linha por ano
    result = result.drop_duplicates("ano", keep="last")
    return result.sort_values("ano").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Parser: sheets mensais por tipo (Pag. 5 e Pag. 9)
# ---------------------------------------------------------------------------
def _parse_mensal_tipo(path: Path, sheet_name: str) -> pd.DataFrame:
    """
    Faz o parse de sheet mensal por tipo.
    Retorna DataFrame hierarquico com colunas:
      codigo, nome, classe_pai, is_categoria, <YYYY-MM>, ...
    """
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)

    # Encontra linha de cabecalho (contendo datas nas colunas)
    header_row = None
    for i, row in raw.iterrows():
        n_datas = sum(1 for v in row if _parse_date_header(v) is not None)
        if n_datas >= 3:
            header_row = i
            break

    if header_row is None:
        raise ValueError(f"Cabecalho de meses nao encontrado em {sheet_name}")

    # Mapeia indice de coluna -> "YYYY-MM"
    month_col_map = {}
    for ci, v in enumerate(raw.iloc[header_row]):
        if ci < 2:
            continue
        mes_str = _parse_date_header(v)
        if mes_str:
            month_col_map[ci] = mes_str

    if not month_col_map:
        raise ValueError(f"Nenhuma coluna de mes em {sheet_name}")

    data_start = header_row + 1
    df = raw.iloc[data_start:].copy().reset_index(drop=True)

    rows = []
    current_classe = None

    for _, row in df.iterrows():
        codigo_raw = row.iloc[0]
        nome_raw = row.iloc[1] if len(row) > 1 else None

        if pd.isna(nome_raw) or str(nome_raw).strip() == "":
            continue

        nome = str(nome_raw).strip()
        if not nome or nome.lower() in ("nan", "total", "tipos anbima"):
            continue

        # Codigo pode ser float (272.0) ou NaN
        sem_codigo = pd.isna(codigo_raw) or str(codigo_raw).strip() == ""
        codigo = None if sem_codigo else str(int(float(codigo_raw)))

        # Filtra linhas de rodape: texto longo sem codigo
        if sem_codigo and len(nome) > 60:
            continue

        # Determina se e categoria ou subcategoria
        # Regra: linha sem codigo E cujo nome NAO comeca com o nome da classe atual
        # => nova categoria. Senao => sub-agregado da classe atual (trata como subcategoria)
        if sem_codigo:
            if current_classe and nome.startswith(current_classe):
                # Sub-agregado (ex: "FII Tijolo Renda" dentro de "FII") -> subcategoria
                is_categoria = False
            else:
                is_categoria = True
                current_classe = nome
        else:
            is_categoria = False

        valores = {}
        for ci, mes_str in month_col_map.items():
            val = row.iloc[ci] if ci < len(row) else None
            val_f = pd.to_numeric(val, errors="coerce")
            valores[mes_str] = round(float(val_f) / 1000, 3) if pd.notna(val_f) else None

        rows.append({
            "codigo": codigo,
            "nome": nome,
            "classe_pai": current_classe if not is_categoria else None,
            "is_categoria": is_categoria,
            **valores,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Funcao publica principal
# ---------------------------------------------------------------------------
def parse_boletim(path: str | Path) -> dict[str, pd.DataFrame]:
    """
    Extrai todos os DataFrames relevantes de um arquivo Boletim.xlsx.

    Retorna dict com chaves:
      'pl_anual', 'captacao_anual', 'captacao_mensal_classe',
      'pl_mensal', 'captacao_mensal'
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    xl = pd.ExcelFile(path)
    sheets = xl.sheet_names

    def find_sheet(*keywords):
        for s in sheets:
            sl = _normalize(s)
            if all(_normalize(k) in sl for k in keywords):
                return s
        return None

    result = {}

    # PL anual (sheet 4)
    s = find_sheet("pl", "classe")
    if s:
        try:
            result["pl_anual"] = _parse_pl_classe(path, s)
            print(f"  [OK] pl_anual: {len(result['pl_anual'])} anos ({s})")
        except Exception as e:
            print(f"  [ERRO] pl_anual: {e}")

    # Captacao anual + mensal por classe (sheet 8)
    s = find_sheet("cap", "classe")
    if not s:
        s = find_sheet("captacao", "classe")
    if s:
        try:
            dados_classe = _parse_classe_sheet(path, s)
            result["captacao_anual"] = dados_classe["anual"]
            result["captacao_mensal_classe"] = dados_classe["mensal"]
            print(f"  [OK] captacao_anual: {len(result['captacao_anual'])} anos ({s})")
            print(f"  [OK] captacao_mensal_classe: {len(result['captacao_mensal_classe'])} meses ({s})")
        except Exception as e:
            print(f"  [ERRO] captacao_classe: {e}")

    # PL mensal por tipo (sheet 5)
    s = find_sheet("pl", "tipo")
    if s:
        try:
            result["pl_mensal"] = _parse_mensal_tipo(path, s)
            print(f"  [OK] pl_mensal: {len(result['pl_mensal'])} linhas ({s})")
        except Exception as e:
            print(f"  [ERRO] pl_mensal: {e}")

    # Captacao mensal por tipo (sheet 9)
    s = find_sheet("cap", "tipo")
    if not s:
        s = find_sheet("captacao", "tipo")
    if s:
        try:
            result["captacao_mensal"] = _parse_mensal_tipo(path, s)
            print(f"  [OK] captacao_mensal: {len(result['captacao_mensal'])} linhas ({s})")
        except Exception as e:
            print(f"  [ERRO] captacao_mensal: {e}")

    return result


if __name__ == "__main__":
    import sys
    arquivo = sys.argv[1] if len(sys.argv) > 1 else "data/raw/Boletim.xlsx"
    print(f"Parsing: {arquivo}")
    dados = parse_boletim(arquivo)
    for k, df in dados.items():
        print(f"\n--- {k} ({len(df)} rows) ---")
        cols = [c for c in df.columns if not c.startswith("20")][:8]
        print(df[cols].head(3).to_string())
