import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { DadoMensalResumo, CORES_CLASSES } from "../types/fundos";

interface Props {
  captacaoMensal: DadoMensalResumo[];
}

// Meses em português abreviado
const MESES_PT: Record<string, string> = {
  "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
  "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
  "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
};

function formatMes(periodo: string): string {
  // "YYYY-MM" → "Jan/25"
  const [ano, mes] = periodo.split("-");
  return `${MESES_PT[mes] ?? mes}/${ano.slice(2)}`;
}

function fmtSinal(val: number | null | undefined): string {
  if (val == null) return "–";
  const s = val > 0 ? "+" : "";
  return s + val.toFixed(1).replace(".", ",");
}

// Extrai as classes presentes nos dados (exclui 'periodo' e chaves de meta)
function getClasses(dados: DadoMensalResumo[]): string[] {
  if (!dados.length) return [];
  const keys = Object.keys(dados[0]).filter((k) => k !== "periodo");
  // Ordena preferencialmente: renda_fixa, multimercado, acoes, ...
  const ordem = [
    "renda_fixa", "multimercado", "acoes", "cambial",
    "previdencia", "etf", "fidc", "fip", "fiagro", "fii", "offshore",
  ];
  return [
    ...ordem.filter((k) => keys.includes(k)),
    ...keys.filter((k) => !ordem.includes(k)),
  ];
}

const CLASSE_LABELS_PT: Record<string, string> = {
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

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm max-w-xs">
      <p className="font-semibold text-gray-800 mb-2">{label}</p>
      {payload
        .sort((a, b) => b.value - a.value)
        .map((entry) => (
          <div key={entry.name} className="flex items-center gap-2">
            <span
              className="inline-block w-3 h-2 rounded-sm"
              style={{ background: entry.color }}
            />
            <span className="text-gray-600 flex-1">{entry.name}:</span>
            <span
              className={`font-medium ${entry.value < 0 ? "text-red-600" : "text-green-700"}`}
            >
              {entry.value > 0 ? "+" : ""}
              {entry.value.toFixed(1).replace(".", ",")} bi
            </span>
          </div>
        ))}
    </div>
  );
}

export default function TabelaMensal({ captacaoMensal }: Props) {
  if (!captacaoMensal.length) {
    return (
      <p className="text-gray-500 text-sm">
        Dados mensais não disponíveis.
      </p>
    );
  }

  const classes = getClasses(captacaoMensal);
  const periodos = captacaoMensal.map((d) => d.periodo);

  // Prepara dados para o gráfico
  const chartData = captacaoMensal.map((d) => ({
    mes: formatMes(d.periodo),
    ...Object.fromEntries(
      classes.map((c) => [
        CLASSE_LABELS_PT[c] ?? c,
        typeof d[c] === "number" ? d[c] : null,
      ])
    ),
  }));

  return (
    <div>
      <h3 className="text-base font-semibold text-gray-700 mb-3">
        Captação Líquida por Classe — Mensal (R$ bilhões)
      </h3>

      {/* Tabela */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-anbima-blue text-white">
              <th className="text-left px-3 py-2.5 font-medium w-36 sticky left-0 bg-anbima-blue">
                Classe
              </th>
              {periodos.map((p) => (
                <th key={p} className="text-right px-3 py-2.5 font-medium whitespace-nowrap">
                  {formatMes(p)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {classes.map((chave, idx) => {
              const label = CLASSE_LABELS_PT[chave] ?? chave;
              const isRF = chave === "renda_fixa";
              const hasSem = isRF && captacaoMensal.some((d) => d["renda_fixa_sem_credito"] != null);
              const hasCom = isRF && captacaoMensal.some((d) => d["renda_fixa_com_credito"] != null);
              return (
                <React.Fragment key={chave}>
                  <tr className={idx % 2 === 0 ? "bg-white" : "bg-blue-50/30"}>
                    <td className="px-3 py-2 font-medium text-gray-700 sticky left-0 bg-inherit">
                      {label}
                    </td>
                    {captacaoMensal.map((d) => {
                      const val = d[chave] as number | null;
                      const neg = val != null && val < 0;
                      return (
                        <td
                          key={d.periodo}
                          className={`px-3 py-2 text-right tabular-nums ${
                            neg ? "text-red-600" : "text-gray-800"
                          }`}
                        >
                          {fmtSinal(val)}
                        </td>
                      );
                    })}
                  </tr>
                  {hasSem && (
                    <tr className="bg-anbima-blue-light/10">
                      <td className="pl-7 pr-3 py-1.5 text-xs text-gray-500 italic sticky left-0 bg-anbima-blue-light/10">
                        ↳ Sem Crédito
                      </td>
                      {captacaoMensal.map((d) => {
                        const val = d["renda_fixa_sem_credito"] as number | null;
                        const neg = val != null && val < 0;
                        return (
                          <td
                            key={d.periodo}
                            className={`px-3 py-1.5 text-right tabular-nums text-xs ${
                              neg ? "text-red-500" : "text-gray-500"
                            }`}
                          >
                            {fmtSinal(val)}
                          </td>
                        );
                      })}
                    </tr>
                  )}
                  {hasCom && (
                    <tr className="bg-anbima-blue-light/10">
                      <td className="pl-7 pr-3 py-1.5 text-xs text-gray-500 italic sticky left-0 bg-anbima-blue-light/10">
                        ↳ Com Crédito
                      </td>
                      {captacaoMensal.map((d) => {
                        const val = d["renda_fixa_com_credito"] as number | null;
                        const neg = val != null && val < 0;
                        return (
                          <td
                            key={d.periodo}
                            className={`px-3 py-1.5 text-right tabular-nums text-xs ${
                              neg ? "text-red-500" : "text-gray-500"
                            }`}
                          >
                            {fmtSinal(val)}
                          </td>
                        );
                      })}
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Gráfico de linha */}
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ left: 10, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `${v.toFixed(0)}`}
              label={{
                value: "R$ bi",
                angle: -90,
                position: "insideLeft",
                offset: -5,
                style: { fontSize: 11, fill: "#6b7280" },
              }}
            />
            <ReferenceLine y={0} stroke="#374151" strokeWidth={1.5} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {/* Exibe apenas as 4 principais classes no gráfico para não poluir */}
            {["renda_fixa", "multimercado", "acoes", "previdencia"]
              .filter((c) => classes.includes(c))
              .map((chave) => (
                <Line
                  key={chave}
                  type="monotone"
                  dataKey={CLASSE_LABELS_PT[chave] ?? chave}
                  stroke={CORES_CLASSES[chave] ?? "#888"}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
