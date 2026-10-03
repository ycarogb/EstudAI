"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Upload, ArrowLeft } from "lucide-react";
import { Button } from "@/components/Button";
import { LlmSettingsButton } from "@/components/LlmSettingsButton";
import { LogoMark } from "@/components/Logo";
import { createProject, importMendeley } from "@/lib/api";

export default function RevisaoEntryPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const project = await createProject(
        "Revisão Mendeley",
        "Coleção importada do Mendeley"
      );
      await importMendeley(project.id, file);
      router.push(`/revisao/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao importar coleção");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-50 to-white">
      <header className="border-b border-brand-100 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-4xl items-center gap-3 px-6 py-4">
          <Link href="/" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Link href="/" aria-label="Página inicial">
            <LogoMark className="h-7 w-7" />
          </Link>
          <span className="flex-1 text-lg font-semibold text-brand-900">Revisão Mendeley</span>
          <LlmSettingsButton />
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="text-3xl font-bold text-gray-900">Analise sua coleção do Mendeley</h1>
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <strong>Importante:</strong> arquivos RIS/BibTeX trazem apenas metadados (título, autores, DOI).
          Para analisar métodos, resultados e lacunas do <em>corpo</em> dos trabalhos, anexe os{" "}
          <strong>PDFs</strong> na próxima tela. O EstudAI também tentará buscar resumos automaticamente pelo DOI.
        </div>
        <p className="mt-4 text-gray-600">
          Exporte sua coleção no Mendeley (BibTeX ou RIS), importe aqui e depois clique em
          <strong> Analisar coleção </strong>
          para extrair lacunas, métodos, escopo e referências compartilhadas.
        </p>

        <ol className="mt-8 space-y-3 text-sm text-gray-700">
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">1</span>
            No Mendeley: selecione a coleção → File → Export → BibTeX ou RIS
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">2</span>
            Importe o arquivo abaixo
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">3</span>
            Clique em <strong>Analisar coleção</strong> na próxima tela
          </li>
        </ol>

        <input
          ref={inputRef}
          type="file"
          accept=".ris,.bib,.bibtex"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />

        <div className="mt-10 rounded-2xl border-2 border-dashed border-gray-300 bg-white p-10 text-center">
          <Upload className="mx-auto h-10 w-10 text-gray-400" />
          <p className="mt-4 text-sm text-gray-600">Arquivo exportado do Mendeley (.bib ou .ris)</p>
          <Button
            className="mt-6"
            onClick={() => inputRef.current?.click()}
            disabled={loading}
          >
            {loading ? "Importando..." : "Selecionar arquivo"}
          </Button>
        </div>

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}
      </main>
    </div>
  );
}
