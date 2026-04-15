import { useEffect, useState } from "react";
import TabelaAnual from "./components/TabelaAnual";
import TabelaMensal from "./components/TabelaMensal";
import TabelaDetalhada from "./components/TabelaDetalhada";
import {
  DadoAnual,
  DadoMensalResumo,
  TabelaDetalhada as TDados,
  Meta,
} from "./types/fundos";

const BASE = import.meta.env.BASE_URL;

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

type Aba = "visao-geral" | "tabela-detalhada";

function formatDataBR(iso: string | null | undefined): string {
  if (!iso) return "–";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatMesRef(periodo: string | null | undefined): string {
  if (!periodo) return "–";
  const meses: Record<string, string> = {
    "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
    "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
    "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
  };
  const [ano, mes] = periodo.split("-");
  return `${meses[mes] ?? mes}/${ano}`;
}

export default function App() {
  const [aba, setAba] = useState<Aba>("visao-geral");
  const [captacaoAnual, setCaptacaoAnual] = useState<DadoAnual[]>([]);
  const [plAnual, setPlAnual] = useState<DadoAnual[]>([]);
  const [captacaoMensal, setCaptacaoMensal] = useState<DadoMensalResumo[]>([]);
  const [tabelaDetalhada, setTabelaDetalhada] = useState<TDados | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [ca, pa, cm, td, mt] = await Promise.all([
          fetchJson<DadoAnual[]>("data/captacao_anual.json"),
          fetchJson<DadoAnual[]>("data/pl_anual.json"),
          fetchJson<DadoMensalResumo[]>("data/captacao_mensal.json"),
          fetchJson<TDados>("data/tabela_detalhada.json"),
          fetchJson<Meta>("data/meta.json"),
        ]);

        if (!ca && !pa) {
          setErro(
            "Dados não encontrados. Execute o pipeline Python primeiro: python scripts/build_data.py"
          );
        } else {
          setCaptacaoAnual(ca ?? []);
          setPlAnual(pa ?? []);
          setCaptacaoMensal(cm ?? []);
          setTabelaDetalhada(td);
          setMeta(mt);
        }
      } catch (e) {
        setErro("Erro ao carregar dados.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      {/* Header */}
      <header className="bg-anbima-blue text-white shadow-md">
        <div className="max-w-screen-xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-white/20 rounded flex items-center justify-center text-lg font-bold">
                  A
                </div>
                <div>
                  <h1 className="text-xl font-bold leading-tight">
                    Fundos de Investimento
                  </h1>
                  <p className="text-blue-200 text-xs">
                    Dashboard de dados ANBIMA
                  </p>
                </div>
              </div>
            </div>
            {meta && (
              <div className="text-right text-sm">
                <p className="text-blue-200 text-xs">Referência</p>
                <p className="font-semibold">
                  {formatMesRef(meta.ultimo_mes_disponivel)}
                </p>
                <p className="text-blue-300 text-xs">
                  Atualizado em {formatDataBR(meta.ultima_atualizacao)}
                </p>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-screen-xl mx-auto px-4">
          <nav className="flex gap-0">
            {(
              [
                { id: "visao-geral", label: "Visão Geral" },
                { id: "tabela-detalhada", label: "Tabela Detalhada" },
              ] as { id: Aba; label: string }[]
            ).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setAba(tab.id)}
                className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                  aba === tab.id
                    ? "border-anbima-blue text-anbima-blue"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <main className="max-w-screen-xl mx-auto px-4 py-6">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-10 h-10 border-3 border-anbima-blue border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-gray-500 text-sm">Carregando dados...</p>
            </div>
          </div>
        )}

        {erro && !loading && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-800 text-sm">
            <p className="font-semibold mb-1">Dados não disponíveis</p>
            <p>{erro}</p>
          </div>
        )}

        {!loading && !erro && (
          <>
            {aba === "visao-geral" && (
              <div className="space-y-8">
                {/* Cards de resumo */}
                {meta && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white rounded-lg border border-gray-200 p-4">
                      <p className="text-xs text-gray-500 mb-1">Período de referência</p>
                      <p className="text-lg font-semibold text-anbima-blue">
                        {formatMesRef(meta.ultimo_mes_disponivel)}
                      </p>
                    </div>
                    <div className="bg-white rounded-lg border border-gray-200 p-4">
                      <p className="text-xs text-gray-500 mb-1">Último ano</p>
                      <p className="text-lg font-semibold text-anbima-blue">
                        {meta.ultimo_ano_disponivel ?? "–"}
                      </p>
                    </div>
                    <div className="bg-white rounded-lg border border-gray-200 p-4">
                      <p className="text-xs text-gray-500 mb-1">Meses disponíveis</p>
                      <p className="text-lg font-semibold text-anbima-blue">
                        {meta.n_meses_disponiveis}
                      </p>
                    </div>
                    <div className="bg-white rounded-lg border border-gray-200 p-4">
                      <p className="text-xs text-gray-500 mb-1">Fonte</p>
                      <p className="text-sm font-medium text-gray-700">ANBIMA Boletim FI</p>
                    </div>
                  </div>
                )}

                {/* Tabelas anuais */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                  <TabelaAnual
                    captacaoAnual={captacaoAnual}
                    plAnual={plAnual}
                  />
                </div>

                {/* Tabela mensal resumo */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                  <TabelaMensal captacaoMensal={captacaoMensal} />
                </div>
              </div>
            )}

            {aba === "tabela-detalhada" && tabelaDetalhada && (
              <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                <TabelaDetalhada dados={tabelaDetalhada} />
              </div>
            )}

            {aba === "tabela-detalhada" && !tabelaDetalhada && (
              <p className="text-gray-500 text-sm">
                Tabela detalhada não disponível.
              </p>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12 py-6 bg-white">
        <div className="max-w-screen-xl mx-auto px-4 text-center text-xs text-gray-400">
          <p>
            Dados extraídos do Boletim de Fundos de Investimento da{" "}
            <a
              href="https://data.anbima.com.br/publicacoes/boletim-de-fundos-de-investimento"
              target="_blank"
              rel="noopener noreferrer"
              className="text-anbima-blue hover:underline"
            >
              ANBIMA
            </a>
            . Valores em R$ bilhões.
          </p>
        </div>
      </footer>
    </div>
  );
}
