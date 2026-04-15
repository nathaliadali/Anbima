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
