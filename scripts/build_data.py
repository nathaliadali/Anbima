"""
build_data.py
-------------
Pipeline mestre: processa todos os Boletins em data/raw/ e gera JSONs
em public/data/ para o frontend React.

Saidas geradas:
  public/data/captacao_anual.json   - Captacao Liquida anual por classe
  public/data/pl_anual.json         - PL anual por classe
  public/data/captacao_mensal.json  - Captacao Liquida mensal por classe (resumo)
  public/data/tabela_detalhada.json - Hierarquia completa por tipo (mensal, captacao)
  public/data/tabela_detalhada_pl.json - Hierarquia por tipo (mensal, PL)
  public/data/meta.json             - Metadados: ultima atualizacao, periodo dos dados

Uso:
    python scripts/build_data.py [--raw data/raw] [--output public/data]
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from parse_boletim import parse_boletim, COLUNAS_CLASSE_ANUAL, _normalize


# ---------------------------------------------------------------------------
# Classes que ficam abertas (com subcategorias) na tabela detalhada
# ---------------------------------------------------------------------------
CLASSES_ABERTAS_NORM = {"renda fixa", "multimercados", "multimercado", "acoes"}

# ---------------------------------------------------------------------------
# Grupos de Renda Fixa para breakdown anual (nomes normalizados)
# ---------------------------------------------------------------------------
RF_SEM_CREDITO_NORM = {
    "renda fixa simples", "renda fixa indexados",
    "renda fixa duracao baixa soberano", "renda fixa duracao media soberano",
    "renda fixa duracao alta soberano", "renda fixa duracao livre soberano",
}

RF_COM_CREDITO_NORM = {
    "renda fixa duracao baixa grau de investimento",
    "renda fixa duracao media grau de investimento",
    "renda fixa duracao alta grau de investimento",
    "renda fixa duracao livre grau de investimento",
    "renda fixa duracao baixa credito livre",
    "renda fixa duracao media credito livre",
    "renda fixa duracao alta credito livre",
    "renda fixa duracao livre credito livre",
}

COLUNAS_RF_GRUPOS = ["renda_fixa_sem_credito", "renda_fixa_com_credito"]


def _parse_aux_rf_grupos(aux_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Le scripts/rf_grupos.json e retorna (rf_cap_anual, rf_pl_anual, rf_cap_mensal).
    Todas as colunas em bilhoes.
    """
    json_path = Path(aux_dir) / "rf_grupos.json"
    if not json_path.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [AVISO] Falha ao ler rf_grupos.json: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    rf_cap         = pd.DataFrame(data.get("captacao", []))
    rf_pl          = pd.DataFrame(data.get("pl", []))
    rf_cap_mensal  = pd.DataFrame(data.get("captacao_mensal", []))
    return rf_cap, rf_pl, rf_cap_mensal


def _compute_rf_grupos_mensal(tipo_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula RF Sem/Com Credito mensais somando os sub-tipos por mes.
    Retorna DataFrame com: periodo, renda_fixa_sem_credito, renda_fixa_com_credito
    """
    if tipo_df.empty:
        return pd.DataFrame()

    month_cols = [c for c in tipo_df.columns
                  if isinstance(c, str) and len(c) == 7 and c[4] == "-"]
    if not month_cols:
        return pd.DataFrame()

    sem_mask = tipo_df["nome"].apply(lambda n: _normalize(str(n)) in RF_SEM_CREDITO_NORM)
    com_mask = tipo_df["nome"].apply(lambda n: _normalize(str(n)) in RF_COM_CREDITO_NORM)

    rf_sem = tipo_df[sem_mask]
    rf_com = tipo_df[com_mask]

    rows = []
    for m in sorted(month_cols):
        def _col_sum(df: pd.DataFrame, col: str) -> float | None:
            if col not in df.columns:
                return None
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            return round(float(vals.sum()), 3) if not vals.empty else None

        rows.append({
            "periodo": m,
            "renda_fixa_sem_credito": _col_sum(rf_sem, m),
            "renda_fixa_com_credito": _col_sum(rf_com, m),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _merge_rf_grupos(aux_df: pd.DataFrame, boletim_df: pd.DataFrame) -> pd.DataFrame:
    """
    Mescla dados de RF grupos do aux e do boletim.
    Boletim tem prioridade (dados mais atualizados); aux preenche anos sem cobertura.
    """
    if aux_df.empty:
        return boletim_df
    if boletim_df.empty:
        return aux_df
    combined = pd.concat([aux_df, boletim_df], ignore_index=True)
    # Para cada ano, mantém a última ocorrência (boletim vem por último no concat)
    combined = combined.sort_values("ano").drop_duplicates("ano", keep="last")
    return combined.reset_index(drop=True)


def _compute_rf_grupos_anual(tipo_df: pd.DataFrame, agg: str = "sum") -> pd.DataFrame:
    """
    Calcula totais anuais de RF Sem Credito e RF Com Credito a partir dos dados
    mensais por tipo (Sheet 9 para captacao, Sheet 5 para PL).
    agg='sum' -> soma todos os meses do ano (captacao)
    agg='dec' -> usa dezembro ou ultimo mes disponivel (PL)
    """
    if tipo_df.empty:
        return pd.DataFrame()

    month_cols = [c for c in tipo_df.columns
                  if isinstance(c, str) and len(c) == 7 and c[4] == "-"]
    if not month_cols:
        return pd.DataFrame()

    sem_mask = tipo_df["nome"].apply(lambda n: _normalize(str(n)) in RF_SEM_CREDITO_NORM)
    com_mask = tipo_df["nome"].apply(lambda n: _normalize(str(n)) in RF_COM_CREDITO_NORM)

    rf_sem = tipo_df[sem_mask]
    rf_com = tipo_df[com_mask]

    years = sorted(set(c[:4] for c in month_cols))
    rows = []

    for year in years:
        year_cols = sorted(c for c in month_cols if c.startswith(year))
        if not year_cols:
            continue

        if agg == "sum":
            def _col_sum(df: pd.DataFrame, cols: list) -> float | None:
                vals = []
                for col in cols:
                    if col in df.columns:
                        vals.extend(pd.to_numeric(df[col], errors="coerce").dropna().tolist())
                return round(float(sum(vals)), 3) if vals else None

            sem_val = _col_sum(rf_sem, year_cols)
            com_val = _col_sum(rf_com, year_cols)
        else:
            dec_col = f"{year}-12" if f"{year}-12" in year_cols else year_cols[-1]

            def _dec_sum(df: pd.DataFrame, col: str) -> float | None:
                if col not in df.columns:
                    return None
                vals = pd.to_numeric(df[col], errors="coerce").dropna()
                return round(float(vals.sum()), 3) if not vals.empty else None

            sem_val = _dec_sum(rf_sem, dec_col)
            com_val = _dec_sum(rf_com, dec_col)

        rows.append({
            "ano": int(year),
            "renda_fixa_sem_credito": sem_val,
            "renda_fixa_com_credito": com_val,
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


CLASSE_LABELS = {
    "renda_fixa": "Renda Fixa",
    "acoes": "Acoes",
    "multimercado": "Multimercado",
    "cambial": "Cambial",
    "previdencia": "Previdencia",
    "etf": "ETF",
    "fidc": "FIDC",
    "fip": "FIP",
    "fiagro": "FIAGRO",
    "fii": "FII",
    "offshore": "Off-shore",
}


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else round(f, 3)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Merging de multiplos boletins
# ---------------------------------------------------------------------------
def _merge_anual(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    # Deduplica por ano, mantendo boletim mais recente
    if "ano" in combined.columns:
        combined = combined.sort_values("ano").drop_duplicates("ano", keep="last")
    return combined.reset_index(drop=True)


def _merge_mensal_classe(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Mescla DataFrames mensais por classe (estrutura plana: 1 linha = 1 mes)."""
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("periodo").drop_duplicates("periodo", keep="last")
    return combined.reset_index(drop=True)


def _merge_mensal_tipo(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Mescla DataFrames hierarquicos mensais por tipo."""
    if not frames:
        return pd.DataFrame()

    all_months = set()
    for df in frames:
        for col in df.columns:
            if isinstance(col, str) and len(col) == 7 and col[4] == "-":
                all_months.add(col)

    month_cols = sorted(all_months)
    combined = pd.concat(frames, ignore_index=True)

    result_rows = []
    for (nome, classe_pai, is_cat, codigo), group in combined.groupby(
        ["nome", "classe_pai", "is_categoria", "codigo"], dropna=False
    ):
        row = {
            "codigo": codigo if pd.notna(codigo) else None,
            "nome": nome,
            "classe_pai": classe_pai if pd.notna(classe_pai) else None,
            "is_categoria": bool(is_cat),
        }
        for m in month_cols:
            if m in group.columns:
                vals = group[m].dropna()
                row[m] = _safe_float(vals.iloc[-1] if len(vals) > 0 else None)
            else:
                row[m] = None
        result_rows.append(row)

    return pd.DataFrame(result_rows)


# ---------------------------------------------------------------------------
# Serializacao JSON
# ---------------------------------------------------------------------------
def _anual_to_json(df: pd.DataFrame, n_anos: int = 5) -> list[dict]:
    if df.empty:
        return []
    df_sorted = df.sort_values("ano", ascending=True).tail(n_anos)
    result = []
    for _, row in df_sorted.iterrows():
        d = {"periodo": str(row["periodo"]), "ano": int(row["ano"])}
        for col in COLUNAS_CLASSE_ANUAL:
            if col in row:
                d[col] = _safe_float(row[col])
        for col in COLUNAS_RF_GRUPOS:
            if col in row:
                d[col] = _safe_float(row[col])
        if "total" in row:
            d["total"] = _safe_float(row["total"])
        result.append(d)
    return result


def _mensal_classe_to_json(df: pd.DataFrame, n_meses: int = 10) -> list[dict]:
    """
    Converte DataFrame mensal por classe (1 row = 1 mes) para lista de dicts.
    """
    if df.empty:
        return []
    df_sorted = df.sort_values("periodo").tail(n_meses)
    result = []
    for _, row in df_sorted.iterrows():
        d = {"periodo": str(row["periodo"])}
        for col in COLUNAS_CLASSE_ANUAL:
            if col in row:
                d[col] = _safe_float(row[col])
        for col in COLUNAS_RF_GRUPOS:
            if col in row:
                d[col] = _safe_float(row[col])
        result.append(d)
    return result


def _is_classe_aberta(nome: str) -> bool:
    """Retorna True se a classe deve ser expandida com subcategorias."""
    nome_norm = _normalize(nome)
    # Remove numeros e caracteres especiais
    import re
    nome_norm = re.sub(r'[^a-z\s]', ' ', nome_norm).strip()
    return any(k in nome_norm for k in CLASSES_ABERTAS_NORM)


# Linhas que NAO sao classes validas (rodapes, totais, etc.)
IGNORAR_NOMES = {
    "total domestico", "total fundos de investimento",
    "total fundos estruturados", "total fundos off shore", "total geral",
    "fundos de investimento", "classes de investimento de estruturados",
    "fundos off shore", "tipos anbima", "anbima informacao publica",
    "anbima - informacao publica",
}

def _is_valida_classe(nome: str) -> bool:
    nome_norm = _normalize(nome)
    # Remove pontuacao para comparacao
    import re
    nome_clean = re.sub(r'[^a-z0-9\s]', ' ', nome_norm).strip()
    nome_clean = re.sub(r'\s+', ' ', nome_clean)
    for ignorar in IGNORAR_NOMES:
        ignorar_clean = re.sub(r'[^a-z0-9\s]', ' ', _normalize(ignorar)).strip()
        ignorar_clean = re.sub(r'\s+', ' ', ignorar_clean)
        if nome_clean == ignorar_clean or ignorar_clean in nome_clean:
            return False
    if len(nome) > 80:  # Linhas de rodape sao textos longos
        return False
    return True


def _tabela_detalhada_to_json(df: pd.DataFrame, n_meses: int = 10) -> dict:
    """
    Gera estrutura hierarquica para a tabela detalhada.
    """
    if df.empty:
        return {"meses": [], "classes": []}

    month_cols = sorted(
        [c for c in df.columns if isinstance(c, str) and len(c) == 7 and c[4] == "-"]
    )
    month_cols = month_cols[-n_meses:]

    cats = df[df["is_categoria"] == True].copy()
    subs = df[df["is_categoria"] == False].copy()

    classes_out = []
    for _, cat_row in cats.iterrows():
        nome = cat_row["nome"]
        if not _is_valida_classe(nome):
            continue

        chave = _normalize(nome).replace(" ", "_")
        import re
        chave = re.sub(r'[^a-z0-9_]', '_', chave)
        aberta = _is_classe_aberta(nome)

        valores_cat = {m: _safe_float(cat_row.get(m)) for m in month_cols}

        subs_classe = subs[subs["classe_pai"] == nome] if "classe_pai" in subs.columns else pd.DataFrame()
        subs_out = []
        if aberta:
            for _, sub_row in subs_classe.iterrows():
                if not _is_valida_classe(sub_row["nome"]):
                    continue
                subs_out.append({
                    "nome": sub_row["nome"],
                    "codigo": sub_row.get("codigo"),
                    "valores": {m: _safe_float(sub_row.get(m)) for m in month_cols},
                })

        classes_out.append({
            "nome": nome,
            "chave": chave,
            "aberta": aberta,
            "valores": valores_cat,
            "subcategorias": subs_out,
        })

    return {"meses": month_cols, "classes": classes_out}


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------
def build(raw_dir: str = "data/raw", output_dir: str = "public/data"):
    raw_path = Path(raw_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    arquivos = sorted(raw_path.glob("*.xlsx")) + sorted(raw_path.glob("*.xls"))
    if not arquivos:
        print(f"Nenhum arquivo Excel encontrado em {raw_dir}")
        return

    print(f"\nEncontrados {len(arquivos)} arquivo(s) para processar:")
    for f in arquivos:
        print(f"  {f.name}")

    all_pl_anual = []
    all_cap_anual = []
    all_cap_mensal_classe = []
    all_pl_mensal = []
    all_cap_mensal = []

    for arquivo in arquivos:
        print(f"\nProcessando: {arquivo.name}")
        try:
            dados = parse_boletim(arquivo)
        except Exception as e:
            print(f"  [ERRO] {e}")
            continue

        if "pl_anual" in dados and not dados["pl_anual"].empty:
            all_pl_anual.append(dados["pl_anual"])
        if "captacao_anual" in dados and not dados["captacao_anual"].empty:
            all_cap_anual.append(dados["captacao_anual"])
        if "captacao_mensal_classe" in dados and not dados["captacao_mensal_classe"].empty:
            all_cap_mensal_classe.append(dados["captacao_mensal_classe"])
        if "pl_mensal" in dados and not dados["pl_mensal"].empty:
            all_pl_mensal.append(dados["pl_mensal"])
        if "captacao_mensal" in dados and not dados["captacao_mensal"].empty:
            all_cap_mensal.append(dados["captacao_mensal"])

    # Mescla
    print("\nMesclando series temporais...")
    pl_anual = _merge_anual(all_pl_anual)
    cap_anual = _merge_anual(all_cap_anual)
    cap_mensal_classe = _merge_mensal_classe(all_cap_mensal_classe)
    pl_mensal = _merge_mensal_tipo(all_pl_mensal)
    cap_mensal = _merge_mensal_tipo(all_cap_mensal)

    # Enriquece com grupos RF (aux historico + boletim recente)
    print("Calculando grupos RF Sem Credito / Com Credito...")
    aux_dir = Path(__file__).parent
    aux_rf_cap, aux_rf_pl, aux_rf_cap_mensal = _parse_aux_rf_grupos(aux_dir)

    boletim_rf_cap = _compute_rf_grupos_anual(cap_mensal, agg="sum")
    boletim_rf_pl  = _compute_rf_grupos_anual(pl_mensal,  agg="dec")
    boletim_rf_cap_mensal = _compute_rf_grupos_mensal(cap_mensal)

    rf_cap = _merge_rf_grupos(aux_rf_cap, boletim_rf_cap)
    rf_pl  = _merge_rf_grupos(aux_rf_pl,  boletim_rf_pl)

    # Merge mensal: aux historico + boletim (boletim tem prioridade)
    if not aux_rf_cap_mensal.empty and not boletim_rf_cap_mensal.empty:
        rf_cap_mensal = pd.concat([aux_rf_cap_mensal, boletim_rf_cap_mensal], ignore_index=True)
        rf_cap_mensal = rf_cap_mensal.sort_values("periodo").drop_duplicates("periodo", keep="last")
    elif not boletim_rf_cap_mensal.empty:
        rf_cap_mensal = boletim_rf_cap_mensal
    else:
        rf_cap_mensal = aux_rf_cap_mensal

    if not cap_anual.empty and not rf_cap.empty:
        cap_anual = cap_anual.merge(rf_cap, on="ano", how="left")
    if not pl_anual.empty and not rf_pl.empty:
        pl_anual = pl_anual.merge(rf_pl, on="ano", how="left")
    if not cap_mensal_classe.empty and not rf_cap_mensal.empty:
        cap_mensal_classe = cap_mensal_classe.merge(rf_cap_mensal, on="periodo", how="left")

    # Serializa
    outputs = {
        "pl_anual.json": _anual_to_json(pl_anual, n_anos=5),
        "captacao_anual.json": _anual_to_json(cap_anual, n_anos=5),
        "captacao_mensal.json": _mensal_classe_to_json(cap_mensal_classe, n_meses=10),
        "tabela_detalhada.json": _tabela_detalhada_to_json(cap_mensal, n_meses=10),
        "tabela_detalhada_pl.json": _tabela_detalhada_to_json(pl_mensal, n_meses=10),
    }

    for filename, data in outputs.items():
        dest = out_path / filename
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        print(f"  [OK] {dest}")

    # Meta
    periodos_mensais = list(cap_mensal_classe["periodo"].unique()) if not cap_mensal_classe.empty else []
    ultimo_mes = max(periodos_mensais) if periodos_mensais else None
    ultimo_ano = int(pl_anual["ano"].max()) if not pl_anual.empty else None

    meta = {
        "ultima_atualizacao": datetime.now().isoformat(),
        "ultimo_mes_disponivel": ultimo_mes,
        "ultimo_ano_disponivel": ultimo_ano,
        "arquivos_processados": [f.name for f in arquivos],
        "n_meses_disponiveis": len(periodos_mensais),
    }
    with open(out_path / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {out_path}/meta.json")

    print(f"\n[OK] Pipeline concluido. Dados em {out_path}/")
    return meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de dados ANBIMA")
    parser.add_argument("--raw", default="data/raw", help="Pasta com boletins Excel")
    parser.add_argument("--output", default="public/data", help="Pasta de saida JSON")
    args = parser.parse_args()
    build(raw_dir=args.raw, output_dir=args.output)
