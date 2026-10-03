"use client";

import { useRef } from "react";
import { Upload } from "lucide-react";
import { Button } from "./Button";

type Props = {
  onImport: (file: File) => void;
  loading?: boolean;
};

export function ImportDialog({ onImport, loading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onImport(file);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".ris,.bib,.bibtex,.csv"
        className="hidden"
        onChange={handleChange}
      />
      <Button
        variant="secondary"
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        className="gap-2"
      >
        <Upload className="h-4 w-4" />
        Importar CAPES
      </Button>
    </>
  );
}
