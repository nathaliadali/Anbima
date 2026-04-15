"""
download_boletins.py
--------------------
Tenta baixar boletins históricos da ANBIMA de:
  https://data.anbima.com.br/publicacoes/boletim-de-fundos-de-investimento

Os boletins são publicados mensalmente. Este script:
1. Acessa a página de publicações
2. Extrai os links de download disponíveis
3. Baixa os arquivos .xlsx para data/raw/

Uso:
    python scripts/download_boletins.py [--anos 5] [--output data/raw]
"""

import argparse
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://data.anbima.com.br"
PUBLICACOES_URL = f"{BASE_URL}/publicacoes/boletim-de-fundos-de-investimento"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def get_download_links(session: requests.Session) -> list[dict]:
    """
    Acessa a página de publicações e extrai links de download dos boletins.
    Retorna lista de dicts: [{url, nome, data}]
    """
    print(f"Acessando: {PUBLICACOES_URL}")
    resp = session.get(PUBLICACOES_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    links = []

    # Procura por links que contenham "boletim" e terminem em .xlsx ou .xls
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)

        # Normaliza URL relativa
        if href.startswith("/"):
            href = BASE_URL + href
        elif not href.startswith("http"):
            continue

        # Filtra por extensão Excel
        if not re.search(r"\.(xlsx?|xls)(\?.*)?$", href, re.IGNORECASE):
            # Tenta pelo texto do link
            if not re.search(r"boletim.*fund|fund.*boletim", text, re.IGNORECASE):
                continue

        # Extrai possível data do texto ou URL
        data_match = re.search(
            r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*[_\-\s/]?(\d{2,4})",
            text + " " + href,
            re.IGNORECASE,
        )
        data_str = data_match.group(0) if data_match else ""

        links.append({"url": href, "nome": text or Path(href).name, "data": data_str})

    # Remove duplicatas por URL
    seen = set()
    unique = []
    for link in links:
        if link["url"] not in seen:
            seen.add(link["url"])
            unique.append(link)

    print(f"  Encontrados {len(unique)} links de download")
    return unique


def download_file(session: requests.Session, url: str, dest: Path) -> bool:
    """Baixa um arquivo para dest. Retorna True se bem-sucedido."""
    if dest.exists():
        print(f"  Já existe: {dest.name}")
        return True

    try:
        print(f"  Baixando: {dest.name} ...")
        resp = session.get(url, headers=HEADERS, timeout=60, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "html" in content_type and b"<html" in resp.content[:100]:
            print(f"  ✗ Resposta HTML (provável login requerido): {url}")
            return False

        dest.write_bytes(resp.content)
        size_kb = dest.stat().st_size / 1024
        print(f"  ✓ {dest.name} ({size_kb:.0f} KB)")
        return True

    except requests.RequestException as e:
        print(f"  ✗ Erro ao baixar {url}: {e}")
        return False


def download_boletins(output_dir: str = "data/raw", anos: int = 5) -> list[Path]:
    """
    Baixa boletins históricos da ANBIMA.
    Retorna lista de caminhos dos arquivos baixados.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    downloaded = []

    try:
        links = get_download_links(session)
    except requests.RequestException as e:
        print(f"Erro ao acessar página da ANBIMA: {e}")
        print("Continuando com arquivos já presentes em data/raw/")
        return list(output_path.glob("*.xlsx"))

    if not links:
        print("Nenhum link encontrado na página. Tentando URLs diretas...")
        links = _generate_direct_urls(anos)

    for link in links:
        url = link["url"]
        # Gera nome de arquivo seguro
        nome = re.sub(r"[^\w\-.]", "_", link["nome"])
        if not nome.endswith(".xlsx"):
            nome += ".xlsx"
        dest = output_path / nome

        success = download_file(session, url, dest)
        if success:
            downloaded.append(dest)

        time.sleep(0.5)  # Respeita o servidor

    return downloaded


def _generate_direct_urls(anos: int) -> list[dict]:
    """
    Gera URLs diretas tentando padrões comuns do site ANBIMA
    para os últimos N anos de boletins mensais.
    """
    links = []
    hoje = datetime.now()
    meses_pt = {
        1: "janeiro", 2: "fevereiro", 3: "marco", 4: "abril",
        5: "maio", 6: "junho", 7: "julho", 8: "agosto",
        9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
    }
    meses_abrev = {
        1: "jan", 2: "fev", 3: "mar", 4: "abr",
        5: "mai", 6: "jun", 7: "jul", 8: "ago",
        9: "set", 10: "out", 11: "nov", 12: "dez",
    }

    data = hoje - timedelta(days=30)  # começa no mês anterior
    for _ in range(anos * 12):
        ano = data.year
        mes = data.month
        mes_pt = meses_pt[mes]
        mes_ab = meses_abrev[mes]
        ano2 = str(ano)[2:]

        # Padrões comuns de URL para boletins ANBIMA
        patterns = [
            f"{BASE_URL}/files/boletim-fundos-investimento-{mes_pt}-{ano}.xlsx",
            f"{BASE_URL}/files/Boletim_FI_{mes_ab}{ano2}.xlsx",
            f"{BASE_URL}/files/boletim-fi-{mes_ab}-{ano}.xlsx",
        ]

        for url in patterns:
            links.append({
                "url": url,
                "nome": f"Boletim_{mes_ab}{ano}.xlsx",
                "data": f"{mes_ab}/{ano}",
            })

        # Volta um mês
        if mes == 1:
            data = data.replace(year=ano - 1, month=12)
        else:
            data = data.replace(month=mes - 1)

    return links


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baixa boletins históricos da ANBIMA")
    parser.add_argument("--anos", type=int, default=5, help="Quantos anos de histórico baixar")
    parser.add_argument("--output", default="data/raw", help="Pasta de saída")
    args = parser.parse_args()

    arquivos = download_boletins(args.output, args.anos)
    print(f"\nTotal baixado: {len(arquivos)} arquivo(s)")
    for f in arquivos:
        print(f"  {f}")
