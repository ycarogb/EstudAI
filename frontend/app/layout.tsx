import type { Metadata } from "next";
import { LlmSettingsDialog } from "@/components/LlmSettingsDialog";
import "./globals.css";

export const metadata: Metadata = {
  title: "EstudAI — Assistente de IA para revisão bibliográfica",
  description:
    "Extraia objetivos, metodologia, resultados e lacunas de até 50 PDFs, encontre correlações entre estudos e converse com um assistente de método científico. Use sua própria chave de IA.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-gray-100 antialiased" suppressHydrationWarning>
        {children}
        <LlmSettingsDialog />
      </body>
    </html>
  );
}
