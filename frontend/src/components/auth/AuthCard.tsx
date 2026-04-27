import type { ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export function AuthCard({ title, subtitle, children }: Props) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-c-bg px-4 py-12">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🐐</div>
          <h1 className="text-2xl font-bold text-c-text">GDF-AutoMon</h1>
          <p className="text-c-text-2 text-sm mt-1">Goat &amp; Dairy Farm Monitoring</p>
        </div>

        <div className="bg-c-surface border border-c-border rounded-2xl p-6 shadow-xl shadow-black/30">
          <h2 className="text-lg font-bold text-c-text mb-1">{title}</h2>
          {subtitle && <p className="text-c-text-2 text-sm mb-5">{subtitle}</p>}
          {children}
        </div>
      </div>
    </div>
  );
}
