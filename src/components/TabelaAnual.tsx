import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  DadoAnual,
  CLASSE_LABELS,
  ORDEM_CLASSES,
  CORES_CLASSES,
} from "../types/fundos";

interface Props {
  captacaoAnual: DadoAnual[];
  plAnual: DadoAnual[];
}

function fmt(val: number | null | undefined): string {
  if (val == null) return "–";
  return val.toFixed(1).replace(".", ",");
}

function fmtSinal(val: number | null | undefined): string {
  if (val == null) return "–";
  const s = val >= 0 ? "+" : "";
  return s + val.toFixed(1).replace(".", ",");
}

// Formata valor no tooltip do gráfico
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
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-gray-800 mb-2">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2">
          <span
            className="inline-block w-3 h-3 rounded-sm"
            style={{ background: entry.color }}
          />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium">
            R$ {entry.value.toFixed(1).replace(".", ",")} bi
          </span>
        </div>
      ))}
    </div>
  );
}

function Tabela({
  dados,
  titulo,
  isCaptacao,
}: {
  dados: DadoAnual[];
  titulo: string;
  isCaptacao: boolean;
}) {
  const anos = dados.map((d) => d.ano);

  // Quais classes têm dados não-nulos
  const classesComDados = ORDEM_CLASSES.filter((c) =>
    dados.some((d) => d[c] != null)
  );

  return (
    <div>
      <h3 className="text-base font-semibold text-gray-700 mb-3">{titulo}</h3>

      {/* Tabela numérica */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-anbima-blue text-white">
              <th className="text-left px-3 py-2.5 font-medium w-36">Classe</th>
              {anos.map((a) => (
                <th key={a} className="text-right px-3 py-2.5 font-medium">
                  {a}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {classesComDados.map((chave, idx) => {
              const label = CLASSE_LABELS[chave] ?? chave;
              return (
                <tr
                  key={chave}
                  className={
                    idx % 2 === 0 ? "bg-white" : "bg-anbima-blue-light/30"
                  }
                >
                  <td className="px-3 py-2 font-medium text-gray-700">
                    {label}
                  </td>
                  {dados.map((d) => {
                    const val = d[chave] as number | null;
                    const neg = isCaptacao && val != null && val < 0;
                    return (
                      <td
                        key={d.ano}
                        className={`px-3 py-2 text-right tabular-nums ${
                          neg ? "text-red-600" : "text-gray-800"
                        }`}
                      >
                        {isCaptacao ? fmtSinal(val) : fmt(val)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {/* Linha de total */}
            <tr className="bg-anbima-blue/5 border-t-2 border-anbima-blue font-semibold">
              <td className="px-3 py-2 text-gray-800">Total</td>
              {dados.map((d) => {
                const val = d.total;
                const neg = isCaptacao && val != null && val < 0;
                return (
                  <td
                    key={d.ano}
                    className={`px-3 py-2 text-right tabular-nums ${
                      neg ? "text-red-600" : "text-gray-800"
                    }`}
                  >
                    {isCaptacao ? fmtSinal(val) : fmt(val)}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      {/* Gráfico de barras */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dados} margin={{ left: 10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="ano" tick={{ fontSize: 12 }} />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `${v.toFixed(0)}bi`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {classesComDados.slice(0, 5).map((chave) => (
              <Bar
                key={chave}
                dataKey={chave}
                name={CLASSE_LABELS[chave] ?? chave}
                fill={CORES_CLASSES[chave] ?? "#888"}
                stackId={isCaptacao ? undefined : "a"}
                radius={isCaptacao ? [2, 2, 0, 0] : undefined}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function TabelaAnual({ captacaoAnual, plAnual }: Props) {
  return (
    <div className="space-y-10">
      <Tabela
        dados={captacaoAnual}
        titulo="Captação Líquida por Classe — Anual (R$ bilhões)"
        isCaptacao={true}
      />
      <Tabela
        dados={plAnual}
        titulo="Patrimônio Líquido por Classe — Anual (R$ bilhões)"
        isCaptacao={false}
      />
    </div>
  );
}
