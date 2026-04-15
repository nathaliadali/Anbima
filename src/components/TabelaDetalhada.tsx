import { useState } from "react";
import type { ReactElement } from "react";
import { TabelaDetalhada as TDados, ClasseFundo } from "../types/fundos";

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

function fmt(val: number | null | undefined, isNeg?: boolean): ReactElement {
  if (val == null) return <span className="text-gray-300">–</span>;
  const s = val > 0 ? "+" : "";
  const text = `${s}${val.toFixed(1).replace(".", ",")}`;
  return (
    <span className={isNeg || val < 0 ? "text-red-600" : val > 0 ? "text-gray-800" : "text-gray-400"}>
      {text}
    </span>
  );
}

// Calcula acumulado de um array de valores
function acum(valores: (number | null)[]): number | null {
  const valids = valores.filter((v): v is number => v != null);
  if (!valids.length) return null;
  return valids.reduce((a, b) => a + b, 0);
}

// Linha de categoria (negrito, sem indentação)
function LinhaCategoria({
  classe,
  meses,
  expanded,
  onToggle,
  acumAno,
  acum12m,
}: {
  classe: ClasseFundo;
  meses: string[];
  expanded: boolean;
  onToggle: () => void;
  acumAno: number | null;
  acum12m: number | null;
}) {
  const temSubs = classe.subcategorias.length > 0;
  return (
    <tr className="bg-anbima-blue/5 border-t border-anbima-blue/20 font-semibold">
      <td
        className="px-3 py-2 text-gray-800 sticky left-0 bg-anbima-blue/5 whitespace-nowrap"
        style={{ minWidth: "220px" }}
      >
        <div className="flex items-center gap-1">
          {temSubs && (
            <button
              onClick={onToggle}
              className="w-4 h-4 flex items-center justify-center text-anbima-blue hover:text-anbima-blue-dark transition-colors rounded"
              title={expanded ? "Recolher" : "Expandir"}
            >
              {expanded ? "▾" : "▸"}
            </button>
          )}
          {!temSubs && <span className="w-4" />}
          <span>{classe.nome}</span>
        </div>
      </td>
      {meses.map((m) => (
        <td key={m} className="px-2 py-2 text-right tabular-nums text-sm">
          {fmt(classe.valores[m])}
        </td>
      ))}
      <td className="px-2 py-2 text-right tabular-nums text-sm border-l border-gray-200">
        {fmt(acumAno)}
      </td>
      <td className="px-2 py-2 text-right tabular-nums text-sm">
        {fmt(acum12m)}
      </td>
    </tr>
  );
}

// Linha de subcategoria (indentada)
function LinhaSubcategoria({
  nome,
  codigo,
  meses,
  valores,
  acumAno,
  acum12m,
  isLast,
}: {
  nome: string;
  codigo: string | null;
  meses: string[];
  valores: Record<string, number | null>;
  acumAno: number | null;
  acum12m: number | null;
  isLast: boolean;
}) {
  return (
    <tr className={`bg-white hover:bg-blue-50/30 transition-colors ${isLast ? "border-b border-gray-200" : ""}`}>
      <td
        className="px-3 py-1.5 text-gray-600 sticky left-0 bg-inherit"
        style={{ minWidth: "220px" }}
      >
        <div className="flex items-center gap-1 pl-5">
          <span className="w-1 h-1 rounded-full bg-gray-300 flex-shrink-0" />
          <span className="text-xs leading-tight">{nome}</span>
          {codigo && (
            <span className="text-xs text-gray-400 ml-auto">{codigo}</span>
          )}
        </div>
      </td>
      {meses.map((m) => (
        <td key={m} className="px-2 py-1.5 text-right tabular-nums text-xs">
          {fmt(valores[m])}
        </td>
      ))}
      <td className="px-2 py-1.5 text-right tabular-nums text-xs border-l border-gray-200">
        {fmt(acumAno)}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums text-xs">
        {fmt(acum12m)}
      </td>
    </tr>
  );
}

export default function TabelaDetalhada({
  dados,
  titulo = "Captação Líquida por Tipo — Mensal (R$ bilhões)",
}: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    // Renda Fixa, Multimercado e Ações começam abertas
    renda_fixa: true,
    multimercado: true,
    acoes: true,
  });

  const { meses, classes } = dados;

  if (!meses.length) {
    return <p className="text-gray-500 text-sm">Dados detalhados não disponíveis.</p>;
  }

  // Determina o início do ano atual (para acum. ano)
  const anoAtual = meses[meses.length - 1]?.slice(0, 4) ?? "";
  const mesesAno = meses.filter((m) => m.startsWith(anoAtual));

  const toggleExpand = (chave: string) => {
    setExpanded((prev) => ({ ...prev, [chave]: !prev[chave] }));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-gray-700">{titulo}</h3>
        <div className="flex gap-2 text-xs">
          <button
            onClick={() =>
              setExpanded(
                Object.fromEntries(classes.map((c) => [c.chave, true]))
              )
            }
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
              <th
                className="text-left px-3 py-2.5 font-medium sticky left-0 bg-anbima-blue"
                style={{ minWidth: "220px" }}
              >
                Classe / Tipo
              </th>
              {meses.map((m) => (
                <th
                  key={m}
                  className="text-right px-2 py-2.5 font-medium whitespace-nowrap"
                  style={{ minWidth: "70px" }}
                >
                  {formatMes(m)}
                </th>
              ))}
              <th className="text-right px-2 py-2.5 font-medium whitespace-nowrap border-l border-blue-400 bg-anbima-blue-dark">
                Acum. {anoAtual}
              </th>
              <th className="text-right px-2 py-2.5 font-medium whitespace-nowrap bg-anbima-blue-dark">
                Acum. 12m
              </th>
            </tr>
          </thead>
          <tbody>
            {classes.map((classe) => {
              const isOpen = !!expanded[classe.chave];
              const mesesAnoVals = mesesAno.map((m) => classe.valores[m] ?? null);
              const acumAnoVal = acum(mesesAnoVals);
              const acum12mVal = acum(meses.map((m) => classe.valores[m] ?? null));

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
                  {isOpen &&
                    classe.subcategorias.map((sub, idx) => {
                      const subMesesAno = mesesAno.map((m) => sub.valores[m] ?? null);
                      return (
                        <LinhaSubcategoria
                          key={sub.codigo ?? sub.nome}
                          nome={sub.nome}
                          codigo={sub.codigo}
                          meses={meses}
                          valores={sub.valores}
                          acumAno={acum(subMesesAno)}
                          acum12m={acum(meses.map((m) => sub.valores[m] ?? null))}
                          isLast={idx === classe.subcategorias.length - 1}
                        />
                      );
                    })}
                </>
              );
            })}

            {/* Linha de total */}
            <tr className="bg-gray-800 text-white font-semibold border-t-2 border-gray-600">
              <td className="px-3 py-2.5 sticky left-0 bg-gray-800">Total</td>
              {meses.map((m) => {
                const total = classes
                  .filter((c) => c.valores[m] != null)
                  .reduce((s, c) => s + (c.valores[m] ?? 0), 0);
                const allNull = classes.every((c) => c.valores[m] == null);
                return (
                  <td key={m} className="px-2 py-2.5 text-right tabular-nums">
                    {allNull ? (
                      <span className="text-gray-500">–</span>
                    ) : (
                      <span className={total < 0 ? "text-red-300" : "text-green-300"}>
                        {total > 0 ? "+" : ""}
                        {total.toFixed(1).replace(".", ",")}
                      </span>
                    )}
                  </td>
                );
              })}
              <td className="px-2 py-2.5 text-right tabular-nums border-l border-gray-600">
                {(() => {
                  const v = acum(
                    mesesAno.map((m) =>
                      classes.reduce((s, c) => s + (c.valores[m] ?? 0), 0)
                    )
                  );
                  if (v == null) return <span className="text-gray-500">–</span>;
                  return (
                    <span className={v < 0 ? "text-red-300" : "text-green-300"}>
                      {v > 0 ? "+" : ""}{v.toFixed(1).replace(".", ",")}
                    </span>
                  );
                })()}
              </td>
              <td className="px-2 py-2.5 text-right tabular-nums">
                {(() => {
                  const v = acum(
                    meses.map((m) =>
                      classes.reduce((s, c) => s + (c.valores[m] ?? 0), 0)
                    )
                  );
                  if (v == null) return <span className="text-gray-500">–</span>;
                  return (
                    <span className={v < 0 ? "text-red-300" : "text-green-300"}>
                      {v > 0 ? "+" : ""}{v.toFixed(1).replace(".", ",")}
                    </span>
                  );
                })()}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-400 mt-2">
        * Valores em R$ bilhões. (+) captação positiva, (–) resgate líquido.
        Clique em ▸ para expandir subcategorias.
      </p>
    </div>
  );
}
