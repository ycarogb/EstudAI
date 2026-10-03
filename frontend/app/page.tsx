"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight,
  FileDown,
  FileSearch,
  Github,
  GraduationCap,
  History,
  KeyRound,
  Library,
  MessagesSquare,
  Network,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { sendChat } from "@/lib/api";
import { openLlmSettings } from "@/lib/llmSettings";
import { Button } from "@/components/Button";
import { Logo } from "@/components/Logo";
import { LlmSettingsButton } from "@/components/LlmSettingsButton";

const REPOSITORY_URL = "https://github.com/ycarogb/EstudAI";

const PROVIDERS = ["OpenAI", "Google Gemini", "Anthropic Claude", "OpenRouter"];

const FEATURES = [
  {
    icon: FileSearch,
    title: "Matriz de extração",
    description:
      "Objetivos, metodologia, resultados e lacunas de até 50 PDFs organizados em uma tabela pronta para a revisão.",
  },
  {
    icon: GraduationCap,
    title: "Artigos, dissertações e teses",
    description:
      "Localiza seções como \"Limitações e sugestões\" e \"Trabalhos futuros\" no corpo do documento, ignorando o sumário.",
  },
  {
    icon: Network,
    title: "Correlações entre estudos",
    description:
      "Conclusões comuns, lacunas recorrentes, padrões metodológicos e divergências entre os trabalhos analisados.",
  },
  {
    icon: MessagesSquare,
    title: "Assistente de método científico",
    description:
      "Converse sobre a sua análise com um orientador virtual direto ao ponto, que fecha cada resposta com um resumo objetivo.",
  },
  {
    icon: History,
    title: "Histórico e retomada",
    description:
      "Cada análise fica salva com a conversa. Reprocesse apenas os PDFs que falharam e recalcule as correlações.",
  },
  {
    icon: FileDown,
    title: "Exportação",
    description: "Relatório em PDF, planilha CSV e referências em BibTeX para levar os resultados adiante.",
  },
];

const STEPS = [
  {
    icon: KeyRound,
    title: "Conecte sua IA",
    description: "Informe a chave do provedor que você já usa. Ela fica apenas no seu navegador.",
  },
  {
    icon: Upload,
    title: "Envie os PDFs",
    description: "Arraste até 50 artigos, dissertações ou teses. O progresso aparece em tempo real.",
  },
  {
    icon: Sparkles,
    title: "Explore os resultados",
    description: "Revise a matriz, leia as correlações e aprofunde as lacunas conversando com o assistente.",
  },
];

const SAMPLE_ROWS = [
  {
    work: "Silva et al. (2024)",
    method: "Estudo de caso, entrevistas",
    gap: "Amostra restrita a uma região",
  },
  {
    work: "Souza (2023) — Tese",
    method: "Métodos mistos, survey",
    gap: "Ausência de análise longitudinal",
  },
  {
    work: "Lee & Park (2022)",
    method: "Revisão sistemática",
    gap: "Poucos estudos no Sul Global",
  },
];

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    setError(null);
    try {
      const res = await sendChat(query.trim());
      if (res.project_id) {
        router.push(`/project/${res.project_id}`);
      } else {
        setError("Não foi possível criar o projeto. Verifique se o backend está rodando.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao iniciar revisão");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-40 border-b border-gray-100 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
          <Link href="/" aria-label="EstudAI">
            <Logo />
          </Link>
          <nav className="hidden flex-1 items-center gap-6 text-sm text-gray-600 md:flex">
            <Link href="/analise-pdf" className="hover:text-gray-900">
              Análise de PDFs
            </Link>
            <Link href="/revisao" className="hover:text-gray-900">
              Revisão Mendeley
            </Link>
            <a href="#busca" className="hover:text-gray-900">
              Busca
            </a>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <a
              href={REPOSITORY_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-full p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-900"
              aria-label="Código no GitHub"
            >
              <Github className="h-5 w-5" />
            </a>
            <LlmSettingsButton />
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_50%_at_50%_0%,rgba(37,99,235,0.14),transparent),radial-gradient(40%_40%_at_90%_20%,rgba(124,58,237,0.12),transparent)]" />
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-20 pt-16 lg:grid-cols-2 lg:pt-24">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
                <Sparkles className="h-3.5 w-3.5" />
                Assistente de IA para pesquisa acadêmica
              </span>
              <h1 className="mt-5 text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
                Da pilha de PDFs às{" "}
                <span className="bg-gradient-to-r from-brand-600 to-violet-600 bg-clip-text text-transparent">
                  lacunas de pesquisa
                </span>
              </h1>
              <p className="mt-5 text-lg leading-relaxed text-gray-600">
                O EstudAI lê seus artigos, dissertações e teses, monta a matriz de extração da revisão
                bibliográfica e mostra o que os estudos têm em comum — e o que ainda falta pesquisar.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/analise-pdf"
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-brand-600/25 transition hover:bg-brand-700"
                >
                  Analisar meus PDFs
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/revisao"
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-5 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
                >
                  <Library className="h-4 w-4" />
                  Importar do Mendeley
                </Link>
              </div>
              <div className="mt-8">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                  Funciona com a sua chave de
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {PROVIDERS.map((provider) => (
                    <span
                      key={provider}
                      className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-600"
                    >
                      {provider}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <div className="rounded-2xl border border-gray-200 bg-white shadow-2xl shadow-brand-900/10">
                <div className="flex items-center gap-1.5 border-b border-gray-100 px-4 py-3">
                  <span className="h-2.5 w-2.5 rounded-full bg-red-300" />
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
                  <span className="ml-3 text-xs text-gray-400">Matriz de extração · 3 trabalhos</span>
                </div>
                <div className="overflow-hidden p-4">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="text-gray-400">
                        <th className="pb-2 font-medium">Trabalho</th>
                        <th className="pb-2 font-medium">Metodologia</th>
                        <th className="pb-2 font-medium">Lacuna</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {SAMPLE_ROWS.map((row) => (
                        <tr key={row.work} className="text-gray-700">
                          <td className="py-2.5 pr-3 font-medium text-gray-900">{row.work}</td>
                          <td className="py-2.5 pr-3">{row.method}</td>
                          <td className="py-2.5">
                            <span className="rounded bg-violet-50 px-1.5 py-0.5 text-violet-700">{row.gap}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="relative -mt-3 ml-auto mr-6 max-w-xs rounded-2xl border border-gray-200 bg-white p-4 shadow-xl">
                <div className="flex items-center gap-2 text-xs font-semibold text-gray-900">
                  <MessagesSquare className="h-4 w-4 text-brand-600" />
                  Assistente de método
                </div>
                <p className="mt-2 text-xs leading-relaxed text-gray-600">
                  <strong className="text-gray-900">Em resumo:</strong> os três estudos convergem na
                  falta de dados longitudinais — um bom recorte para a sua tese.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-gray-100 bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight text-gray-900">
                Tudo o que a revisão bibliográfica exige
              </h2>
              <p className="mt-3 text-gray-600">
                Pensado para mestrandos, doutorandos e pesquisadores que precisam ir além do resumo.
              </p>
            </div>
            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-2xl border border-gray-200 bg-white p-6 transition hover:-translate-y-0.5 hover:shadow-lg"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-violet-600 text-white">
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-4 font-semibold text-gray-900">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20">
          <div className="mx-auto max-w-6xl px-6">
            <h2 className="text-center text-3xl font-bold tracking-tight text-gray-900">Como funciona</h2>
            <ol className="mt-12 grid gap-8 md:grid-cols-3">
              {STEPS.map((step, index) => (
                <li key={step.title} className="text-center">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
                    <step.icon className="h-6 w-6" />
                  </div>
                  <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-brand-600">
                    Passo {index + 1}
                  </p>
                  <h3 className="mt-1 text-lg font-semibold text-gray-900">{step.title}</h3>
                  <p className="mt-2 text-sm text-gray-600">{step.description}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="px-6">
          <div className="mx-auto flex max-w-6xl flex-col items-start gap-6 rounded-3xl bg-gradient-to-br from-brand-600 to-violet-700 p-10 text-white md:flex-row md:items-center">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/15">
              <ShieldCheck className="h-7 w-7" />
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold">Traga sua própria chave</h2>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-white/85">
                Você escolhe o provedor e o modelo, e paga direto a quem fornece a IA. A chave fica salva
                apenas no seu navegador e é usada somente durante as análises — nunca é armazenada no
                servidor.
              </p>
            </div>
            <button
              type="button"
              onClick={openLlmSettings}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-brand-700 transition hover:bg-brand-50"
            >
              <KeyRound className="h-4 w-4" />
              Configurar IA
            </button>
          </div>
        </section>

        <section id="busca" className="scroll-mt-20 py-20">
          <div className="mx-auto max-w-3xl px-6">
            <div className="text-center">
              <h2 className="text-3xl font-bold tracking-tight text-gray-900">Comece pela busca</h2>
              <p className="mt-3 text-gray-600">
                Descreva seu tema em linguagem natural e encontre trabalhos em OpenAlex, Semantic Scholar e
                BDTD.
              </p>
            </div>

            <form onSubmit={handleStart} className="mt-10">
              <div className="rounded-2xl border border-gray-200 bg-white p-2 shadow-lg">
                <div className="flex items-start gap-3 p-4">
                  <Search className="mt-1 h-5 w-5 text-gray-400" />
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    rows={3}
                    placeholder="Ex: Inteligência artificial aplicada à educação superior no Brasil, com foco em avaliação de aprendizagem..."
                    className="flex-1 resize-none border-0 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-0"
                    disabled={loading}
                  />
                </div>
                <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3">
                  <p className="text-xs text-gray-500">
                    Fontes: OpenAlex · Semantic Scholar · BDTD · Importação CAPES
                  </p>
                  <Button type="submit" disabled={loading || !query.trim()}>
                    {loading ? "Buscando..." : "Buscar trabalhos"}
                  </Button>
                </div>
              </div>
            </form>

            {error && (
              <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
            )}
          </div>
        </section>
      </main>

      <footer className="border-t border-gray-100 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-gray-500 sm:flex-row">
          <Logo />
          <p>
            Feito por{" "}
            <a
              href="https://github.com/ycarogb"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-gray-700 hover:text-brand-600"
            >
              Ycaro Batalha
            </a>{" "}
            · Código aberto sob licença MIT
          </p>
        </div>
      </footer>
    </div>
  );
}
