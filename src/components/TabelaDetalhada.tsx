import { useState } from "react";
import type { ReactElement } from "react";
import { TabelaDetalhada as TDados, ClasseFundo, Subcategoria } from "../types/fundos";

interface Props {
  dados: TDados;
  titulo?: string;
}

const MESES_PT: Record<string, string> = {
  "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
  "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
  "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
};

function formatMes(periodo: string): string {
  const [ano, mes] = periodo.split("-");
  return `${MESES_PT[mes] ?? mes}/${ano.slice(2)}`;
}

function fmt(val: number | null | undefined): ReactElement {
  if (val == null) return <span className="text-gray-300">–</span>;
  const s = val > 0 ? "+" : "";
  const text = `${s}${val.toFixed(1).replace(".", ",")}`;
  return (
    <span className={val < 0 ? "text-red-500" : val > 0 ? "text-gray-800" : "text-gray-400"}>
      {text}
    </span>
  );
}

function fmtTotal(val: number | null | undefined): ReactElement {
  if (val == null) return <span className="text-blue-300">–</span>;
  const s = val > 0 ? "+" : "";
  const text = `${s}${val.toFixed(1).replace(".", ",")}`;
  return (
    <span className={val < 0 ? "text-red-300" : "text-green-300"}>{text}</span>
  );
}

function acum(valores: (number | null)[]): number | null {
  const valids = valores.filter((v): v is number => v != null);
  if (!valids.length) return null;
  return valids.reduce((a, b) => a + b, 0);
}

// ---------------------------------------------------------------------------
// Estrutura hierárquica de Renda Fixa
// ---------------------------------------------------------------------------
type RFItemDef     = { type: "item"; nome: string };
type RFSubgroupDef = { type: "subgroup"; nome: string; items: string[] };
type RFGroupDef    = { type: "group"; nome: string; children: Array<RFItemDef | RFSubgroupDef> };
type RFEntryDef    = RFGroupDef | RFItemDef;

const RF_ESTRUTURA: RFEntryDef[] = [
  {
    type: "group", nome: "Sem Crédito",
    children: [
      { type: "item", nome: "Renda Fixa Simples" },
      { type: "item", nome: "Renda Fixa Indexados" },
    ],
  },
  {
    type: "group", nome: "Soberano",
    children: [
      { type: "item", nome: "Renda Fixa Duração Baixa Soberano" },
      { type: "item", nome: "Renda Fixa Duração Média Soberano" },
      { type: "item", nome: "Renda Fixa Duração Alta Soberano" },
      { type: "item", nome: "Renda Fixa Duração Livre Soberano" },
    ],
  },
  {
    type: "group", nome: "Com Crédito",
    children: [
      {
        type: "subgroup", nome: "Grau de Investimento",
        items: [
          "Renda Fixa Duração Baixa Grau de Investimento",
          "Renda Fixa Duração Média Grau de Investimento",
          "Renda Fixa Duração Alta Grau de Investimento",
          "Renda Fixa Duração Livre Grau de Investimento",
        ],
      },
      {
        type: "subgroup", nome: "Livre",
        items: [
          "Renda Fixa Duração Baixa Crédito Livre",
          "Renda Fixa Duração Média Crédito Livre",
          "Renda Fixa Duração Alta Crédito Livre",
          "Renda Fixa Duração Livre Crédito Livre",
        ],
      },
    ],
  },
  { type: "item", nome: "Renda Fixa Investimento no Exterior" },
  { type: "item", nome: "Renda Fixa Dívida Externa" },
];

function normNome(nome: string): string {
  return nome.toLowerCase().trim();
}
function findSub(subs: Subcategoria[], nome: string): Subcategoria | undefined {
  const norm = normNome(nome);
  return subs.find((s) => normNome(s.nome) === norm);
}

function renderItemRow(
  sub: Subcategoria, meses: string[], mesesAno: string[], indent: string,
): ReactElement {
  const acumAno = acum(mesesAno.map((m) => sub.valores[m] ?? null));
  const acum12m = acum(meses.map((m) => sub.valores[m] ?? null));
  return (
    <tr key={sub.codigo ?? sub.nome} className="bg-white hover:bg-anbima-blue-light/30 transition-colors">
      <td className="px-3 py-1.5 text-gray-600 sticky left-0 bg-inherit" style={{ minWidth: "220px" }}>
        <div className={`flex items-center gap-1 ${indent}`}>
          <span className="w-1 h-1 rounded-full bg-gray-300 flex-shrink-0" />
          <span className="text-xs leading-tight">{sub.nome}</span>
          {sub.codigo && <span className="text-xs text-gray-400 ml-auto">{sub.codigo}</span>}
        </div>
      </td>
      {meses.map((m) => (
        <td key={m} className="px-2 py-1.5 text-right tabular-nums text-xs">{fmt(sub.valores[m])}</td>
      ))}
      <td className="px-2 py-1.5 text-right tabular-nums text-xs border-l border-gray-200">{fmt(acumAno)}</td>
      <td className="px-2 py-1.5 text-right tabular-nums text-xs">{fmt(acum12m)}</td>
    </tr>
  );
}

function renderRFSubcategorias(classe: ClasseFundo, meses: string[], mesesAno: string[]): ReactElement[] {
  const subs      = classe.subcategorias;
  const totalCols = meses.length + 3;
  const rows: ReactElement[] = [];
  const used = new Set<string>();

  for (const entry of RF_ESTRUTURA) {
    if (entry.type === "item") {
      const sub = findSub(subs, entry.nome);
      if (sub) { used.add(normNome(sub.nome)); rows.push(renderItemRow(sub, meses, mesesAno, "pl-5")); }
    } else {
      rows.push(
        <tr key={`g-${entry.nome}`} className="bg-anbima-blue/10 border-t border-anbima-blue/20">
          <td colSpan={totalCols} className="py-1.5 text-xs font-semibold text-anbima-blue uppercase tracking-wide" style={{ paddingLeft: "2rem" }}>
            {entry.nome}
          </td>
        </tr>
      );
      for (const child of entry.children) {
        if (child.type === "item") {
          const sub = findSub(subs, child.nome);
          if (sub) { used.add(normNome(sub.nome)); rows.push(renderItemRow(sub, meses, mesesAno, "pl-8")); }
        } else {
          rows.push(
            <tr key={`sg-${child.nome}`} className="bg-gray-50 border-t border-gray-100">
              <td colSpan={totalCols} className="py-1 text-xs font-medium text-gray-500 italic" style={{ paddingLeft: "3.5rem" }}>
                {child.nome}
              </td>
            </tr>
          );
          for (const nome of child.items) {
            const sub = findSub(subs, nome);
            if (sub) { used.add(normNome(sub.nome)); rows.push(renderItemRow(sub, meses, mesesAno, "pl-14")); }
          }
        }
      }
    }
  }
  for (const sub of subs) {
    if (!used.has(normNome(sub.nome))) rows.push(renderItemRow(sub, meses, mesesAno, "pl-5"));
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Definição de seções
// ---------------------------------------------------------------------------
const SECOES = [
  {
    id: "fi",
    nome: "Fundos de Investimento",
    matches: (chave: string) =>
      chave.startsWith("renda_fixa") || chave === "acoes" ||
      chave.startsWith("multimercado") || chave === "cambial" ||
      chave === "previdencia" || chave === "etf",
    totalNome: "Total Fundos de Investimento",
  },
  {
    id: "fe",
    nome: "Fundos Estruturados",
    matches: (chave: string) =>
      chave.startsWith("fidc") || chave.startsWith("fip") ||
      chave.startsWith("fiagro") || chave.startsWith("fii"),
    totalNome: "Total Fundos Estruturados",
  },
  {
    id: "fo",
    nome: "Fundos Off-Shore",
    matches: (chave: string) => chave.startsWith("off"),
    totalNome: "Total Fundos Off-Shore",
  },
];

// ---------------------------------------------------------------------------
// Componentes de linha
// ---------------------------------------------------------------------------
function LinhaCategoria({
  classe, meses, expanded, onToggle, acumAno, acum12m,
}: {
  classe: ClasseFundo; meses: string[]; expanded: boolean;
  onToggle: () => void; acumAno: number | null; acum12m: number | null;
}) {
  const temSubs = classe.subcategorias.length > 0;
  return (
    <tr className="bg-anbima-blue/5 border-t border-anbima-blue/20 font-semibold">
      <td className="px-3 py-2 text-gray-800 sticky left-0 bg-anbima-blue/5 whitespace-nowrap" style={{ minWidth: "220px" }}>
        <div className="flex items-center gap-1">
          {temSubs ? (
            <button onClick={onToggle} className="w-4 h-4 flex items-center justify-center text-anbima-blue hover:text-anbima-blue-dark transition-colors rounded" title={expanded ? "Recolher" : "Expandir"}>
              {expanded ? "▾" : "▸"}
            </button>
          ) : <span className="w-4" />}
          <span>{classe.nome}</span>
        </div>
      </td>
      {meses.map((m) => (
        <td key={m} className="px-2 py-2 text-right tabular-nums text-sm">{fmt(classe.valores[m])}</td>
      ))}
      <td className="px-2 py-2 text-right tabular-nums text-sm border-l border-gray-200">{fmt(acumAno)}</td>
      <td className="px-2 py-2 text-right tabular-nums text-sm">{fmt(acum12m)}</td>
    </tr>
  );
}

function LinhaSubcategoria({
  nome, codigo, meses, valores, acumAno, acum12m,
}: {
  nome: string; codigo: string | null; meses: string[];
  valores: Record<string, number | null>; acumAno: number | null; acum12m: number | null;
}) {
  return (
    <tr className="bg-white hover:bg-anbima-blue-light/30 transition-colors">
      <td className="px-3 py-1.5 text-gray-600 sticky left-0 bg-inherit" style={{ minWidth: "220px" }}>
        <div className="flex items-center gap-1 pl-5">
          <span className="w-1 h-1 rounded-full bg-gray-300 flex-shrink-0" />
          <span className="text-xs leading-tight">{nome}</span>
          {codigo && <span className="text-xs text-gray-400 ml-auto">{codigo}</span>}
        </div>
      </td>
      {meses.map((m) => (
        <td key={m} className="px-2 py-1.5 text-right tabular-nums text-xs">{fmt(valores[m])}</td>
      ))}
      <td className="px-2 py-1.5 text-right tabular-nums text-xs border-l border-gray-200">{fmt(acumAno)}</td>
      <td className="px-2 py-1.5 text-right tabular-nums text-xs">{fmt(acum12m)}</td>
    </tr>
  );
}

function LinhaSecaoHeader({ nome, numCols }: { nome: string; numCols: number }) {
  return (
    <tr className="bg-anbima-blue text-white">
      <td colSpan={numCols} className="px-3 py-2 text-sm font-semibold tracking-wide">
        {nome}
      </td>
    </tr>
  );
}

function LinhaTotalSecao({
  nome, meses, mesesAno, secaoClasses,
}: {
  nome: string; meses: string[]; mesesAno: string[]; secaoClasses: ClasseFundo[];
}) {
  const acumAno = acum(mesesAno.map((m) => acum(secaoClasses.map((c) => c.valores[m] ?? null))));
  const acum12m = acum(meses.map((m) => acum(secaoClasses.map((c) => c.valores[m] ?? null))));
  return (
    <tr className="bg-anbima-blue-dark text-white font-semibold border-t border-anbima-blue">
      <td className="px-3 py-2 sticky left-0 bg-anbima-blue-dark">{nome}</td>
      {meses.map((m) => {
        const v = acum(secaoClasses.map((c) => c.valores[m] ?? null));
        return <td key={m} className="px-2 py-2 text-right tabular-nums text-sm">{fmtTotal(v)}</td>;
      })}
      <td className="px-2 py-2 text-right tabular-nums text-sm border-l border-anbima-blue">{fmtTotal(acumAno)}</td>
      <td className="px-2 py-2 text-right tabular-nums text-sm">{fmtTotal(acum12m)}</td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------
export default function TabelaDetalhada({
  dados,
  titulo = "Captação Líquida por Tipo — Mensal (R$ bilhões)",
}: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    renda_fixa: true, multimercados: true, acoes: true,
  });

  const { meses, classes } = dados;

  if (!meses.length) {
    return <p className="text-gray-500 text-sm">Dados detalhados não disponíveis.</p>;
  }

  const anoAtual = meses[meses.length - 1]?.slice(0, 4) ?? "";
  const mesesAno = meses.filter((m) => m.startsWith(anoAtual));
  const numCols  = meses.length + 3;

  const toggleExpand = (chave: string) =>
    setExpanded((prev) => ({ ...prev, [chave]: !prev[chave] }));

  // Separa classes por seção
  const classesSecao = SECOES.map((s) => ({
    ...s,
    items: classes.filter((c) => s.matches(c.chave)),
  }));

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-gray-700">{titulo}</h3>
        <div className="flex gap-2 text-xs">
          <button
            onClick={() => setExpanded(Object.fromEntries(classes.map((c) => [c.chave, true])))}
            className="px-2 py-1 text-anbima-blue border border-anbima-blue rounded hover:bg-anbima-blue-light transition-colors"
          >
            Expandir tudo
          </button>
          <button
            onClick={() => setExpanded({})}
            className="px-2 py-1 text-gray-500 border border-gray-300 rounded hover:bg-gray-100 transition-colors"
          >
            Recolher tudo
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-anbima-blue text-white">
              <th className="text-left px-3 py-2.5 font-medium sticky left-0 bg-anbima-blue" style={{ minWidth: "220px" }}>
                Classe / Tipo
              </th>
              {meses.map((m) => (
                <th key={m} className="text-right px-2 py-2.5 font-medium whitespace-nowrap" style={{ minWidth: "70px" }}>
                  {formatMes(m)}
                </th>
              ))}
              <th className="text-right px-2 py-2.5 font-medium whitespace-nowrap border-l border-anbima-blue-3 bg-anbima-blue-dark">
                Acum. {anoAtual}
              </th>
              <th className="text-right px-2 py-2.5 font-medium whitespace-nowrap bg-anbima-blue-dark">
                Acum. 12m
              </th>
            </tr>
          </thead>
          <tbody>
            {classesSecao.map((secao) => {
              if (!secao.items.length) return null;
              return (
                <>
                  {/* Cabeçalho da seção */}
                  <LinhaSecaoHeader key={`sec-${secao.id}`} nome={secao.nome} numCols={numCols} />

                  {/* Classes da seção */}
                  {secao.items.map((classe) => {
                    const isOpen       = !!expanded[classe.chave];
                    const acumAnoVal   = acum(mesesAno.map((m) => classe.valores[m] ?? null));
                    const acum12mVal   = acum(meses.map((m) => classe.valores[m] ?? null));
                    const isRendaFixa  = classe.chave.includes("renda_fixa");

                    return (
                      <>
                        <LinhaCategoria
                          key={classe.chave}
                          classe={classe}
                          meses={meses}
                          expanded={isOpen}
                          onToggle={() => toggleExpand(classe.chave)}
                          acumAno={acumAnoVal}
                          acum12m={acum12mVal}
                        />
                        {isOpen && isRendaFixa && renderRFSubcategorias(classe, meses, mesesAno)}
                        {isOpen && !isRendaFixa &&
                          classe.subcategorias.map((sub) => {
                            const subAno = mesesAno.map((m) => sub.valores[m] ?? null);
                            return (
                              <LinhaSubcategoria
                                key={sub.codigo ?? sub.nome}
                                nome={sub.nome}
                                codigo={sub.codigo}
                                meses={meses}
                                valores={sub.valores}
                                acumAno={acum(subAno)}
                                acum12m={acum(meses.map((m) => sub.valores[m] ?? null))}
                              />
                            );
                          })
                        }
                      </>
                    );
                  })}

                  {/* Total da seção */}
                  <LinhaTotalSecao
                    key={`tot-${secao.id}`}
                    nome={secao.totalNome}
                    meses={meses}
                    mesesAno={mesesAno}
                    secaoClasses={secao.items}
                  />
                </>
              );
            })}

            {/* Total Geral */}
            <tr className="bg-anbima-blue text-white font-bold border-t-2 border-white">
              <td className="px-3 py-2.5 sticky left-0 bg-anbima-blue">Total Geral</td>
              {meses.map((m) => {
                const v = acum(classes.map((c) => c.valores[m] ?? null));
                return <td key={m} className="px-2 py-2.5 text-right tabular-nums">{fmtTotal(v)}</td>;
              })}
              <td className="px-2 py-2.5 text-right tabular-nums border-l border-anbima-blue-dark">
                {fmtTotal(acum(mesesAno.map((m) => acum(classes.map((c) => c.valores[m] ?? null)))))}
              </td>
              <td className="px-2 py-2.5 text-right tabular-nums">
                {fmtTotal(acum(meses.map((m) => acum(classes.map((c) => c.valores[m] ?? null)))))}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-400 mt-2">
        * Valores em R$ bilhões. (+) captação positiva, (–) resgate líquido.
        FII e Off-Shore exibem "–" pois a captação líquida não é divulgada (ND) pela ANBIMA neste boletim.
      </p>
    </div>
  );
}
