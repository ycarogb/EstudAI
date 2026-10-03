"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, X, FileText } from "lucide-react";
import { Button } from "./Button";
import clsx from "clsx";

const MAX_FILES = 50;

type Props = {
  onAnalyze: (files: File[]) => void;
  disabled?: boolean;
};

export function PdfDropzone({ onAnalyze, disabled }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((incoming: FileList | null) => {
    if (!incoming) return;
    const pdfs = Array.from(incoming).filter((f) =>
      f.name.toLowerCase().endsWith(".pdf")
    );
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      const fresh = pdfs.filter((f) => !existing.has(f.name));
      return [...prev, ...fresh].slice(0, MAX_FILES);
    });
  }, []);

  const remove = (name: string) =>
    setFiles((prev) => prev.filter((f) => f.name !== name));

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={clsx(
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition-colors",
          dragging
            ? "border-brand-500 bg-brand-50"
            : "border-gray-300 bg-white hover:border-brand-400 hover:bg-brand-50",
          disabled && "pointer-events-none opacity-60"
        )}
      >
        <Upload className="mx-auto h-10 w-10 text-gray-400" />
        <p className="mt-3 text-sm font-medium text-gray-700">
          Arraste seus PDFs aqui ou clique para selecionar
        </p>
        <p className="mt-1 text-xs text-gray-500">
          Até {MAX_FILES} arquivos PDF · O texto será extraído e analisado pela IA
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        multiple
        className="hidden"
        onChange={(e) => addFiles(e.target.files)}
        disabled={disabled}
      />

      {files.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2">
            <span className="text-sm font-medium text-gray-700">
              {files.length} arquivo{files.length !== 1 ? "s" : ""} selecionado{files.length !== 1 ? "s" : ""}
              {files.length >= MAX_FILES && (
                <span className="ml-2 text-amber-600">(limite atingido)</span>
              )}
            </span>
            <button
              onClick={() => setFiles([])}
              className="text-xs text-gray-400 hover:text-gray-600"
              disabled={disabled}
            >
              Limpar
            </button>
          </div>

          <ul className="max-h-52 divide-y divide-gray-50 overflow-y-auto">
            {files.map((f) => (
              <li key={f.name} className="flex items-center gap-2 px-4 py-2">
                <FileText className="h-4 w-4 shrink-0 text-brand-500" />
                <span className="flex-1 truncate text-sm text-gray-800">{f.name}</span>
                <span className="shrink-0 text-xs text-gray-400">
                  {(f.size / 1024).toFixed(0)} KB
                </span>
                <button
                  onClick={(e) => { e.stopPropagation(); remove(f.name); }}
                  className="shrink-0 text-gray-300 hover:text-gray-500"
                  disabled={disabled}
                >
                  <X className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>

          <div className="flex justify-end border-t border-gray-100 px-4 py-3">
            <Button
              onClick={() => onAnalyze(files)}
              disabled={disabled || files.length === 0}
            >
              Analisar {files.length} trabalho{files.length !== 1 ? "s" : ""}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
