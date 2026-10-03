import { useId } from "react";
import clsx from "clsx";

export function LogoMark({ className }: { className?: string }) {
  const gradientId = useId();

  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden="true">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2563eb" />
          <stop offset="1" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="12" fill={`url(#${gradientId})`} />
      <path d="M9 19.5c4.5-2.2 9.5-2.2 14 .6v17.4c-4.5-2.6-9.5-2.8-14-.6z" fill="#fff" />
      <path d="M39 19.5c-4.5-2.2-9.5-2.2-14 .6v17.4c4.5-2.6 9.5-2.8 14-.6z" fill="#fff" fillOpacity=".82" />
      <path
        d="M35 5.5c.6 3.4 1.6 4.4 5 5-3.4.6-4.4 1.6-5 5-.6-3.4-1.6-4.4-5-5 3.4-.6 4.4-1.6 5-5z"
        fill="#fde68a"
      />
    </svg>
  );
}

export function Logo({ className, size = "md" }: { className?: string; size?: "md" | "lg" }) {
  return (
    <span className={clsx("inline-flex items-center gap-2", className)}>
      <LogoMark className={size === "lg" ? "h-9 w-9" : "h-7 w-7"} />
      <span
        className={clsx(
          "font-bold tracking-tight text-gray-900",
          size === "lg" ? "text-2xl" : "text-lg"
        )}
      >
        Estud
        <span className="bg-gradient-to-r from-brand-600 to-violet-600 bg-clip-text text-transparent">
          AI
        </span>
      </span>
    </span>
  );
}
