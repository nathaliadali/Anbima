# Dashboard ANBIMA — Fundos de Investimento

Dashboard interativo com dados do **Boletim de Fundos de Investimento da ANBIMA**.

**Site:** [https://seu-usuario.github.io/anbima-dashboard/](https://seu-usuario.github.io/anbima-dashboard/)

## O que exibe

- **Captação Líquida por Classe — Anual** (últimos 5 anos) com gráfico de barras
- **Patrimônio Líquido (PL) por Classe — Anual** (últimos 5 anos) com gráfico empilhado
- **Captação Líquida por Classe — Mensal** (últimos 10 meses) com gráfico de linhas
- **Tabela Detalhada** com hierarquia completa de tipos:
  - Renda Fixa, Multimercado e Ações expandidas com subcategorias
  - Demais classes (Cambial, Previdência, ETF, FIDC, FIP, FIAGRO, FII, Off-shore) como total
  - Colunas: meses + Acum. Ano + Acum. 12m

## Pré-requisitos

- Python 3.11+
- Node.js 20+

## Instalação e uso local

### 1. Instalar dependências Python

```bash
pip install pandas openpyxl requests beautifulsoup4
```

### 2. Adicionar boletim(s) Excel

Coloque os arquivos `.xlsx` baixados do site da ANBIMA em `data/raw/`:

```
data/raw/Boletim.xlsx
```

Link para download: https://data.anbima.com.br/publicacoes/boletim-de-fundos-de-investimento

### 3. (Opcional) Baixar boletins históricos automaticamente

```bash
python scripts/download_boletins.py --anos 3 --output data/raw
```

### 4. Rodar o pipeline de dados

```bash
python scripts/build_data.py
```

Isso gera os arquivos JSON em `public/data/`.

### 5. Instalar dependências Node e rodar o dev server

```bash
npm install
npm run dev
```

Acesse: http://localhost:5173

## Deploy no GitHub Pages

1. Crie um repositório no GitHub e faça push do código:
   ```bash
   git init
   git remote add origin https://github.com/seu-usuario/anbima-dashboard.git
   git add .
   git commit -m "Initial commit"
   git push -u origin main
   ```

2. No GitHub, vá em **Settings → Pages** e configure o source como **GitHub Actions**.

3. O workflow `.github/workflows/deploy.yml` roda automaticamente a cada push na branch `main`.

> **Nota:** Os arquivos `public/data/` estão no `.gitignore`. O pipeline Python roda no GitHub Actions e gera os JSONs antes do build React. Inclua os boletins Excel no repositório em `data/raw/`.

## Estrutura do projeto

```
.
├── scripts/
│   ├── parse_boletim.py       # Parser do Excel
│   ├── download_boletins.py   # Download de histórico
│   └── build_data.py          # Pipeline mestre
├── data/
│   └── raw/                   # Boletins Excel (comitar aqui)
├── public/
│   └── data/                  # JSONs gerados (não comitar)
├── src/
│   ├── components/
│   │   ├── TabelaDetalhada.tsx
│   │   ├── TabelaAnual.tsx
│   │   └── TabelaMensal.tsx
│   ├── types/fundos.ts
│   ├── App.tsx
│   └── main.tsx
└── .github/workflows/deploy.yml
```

## Fonte dos dados

[ANBIMA — Boletim de Fundos de Investimento](https://data.anbima.com.br/publicacoes/boletim-de-fundos-de-investimento)
