"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, FileText, Gauge, Settings, Upload, Video, Mic } from "lucide-react";

import { useAppStore } from "@/lib/store";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
};

const items: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/verify/live", label: "Live Verify", icon: Activity },
  { href: "/verify/upload", label: "Upload Analyze", icon: Upload },
  { href: "/dashboard/audio-verify", label: "Audio Analyze", icon: Mic },
  { href: "/sessions", label: "Sessions", icon: Video },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, isLiveActive } = useAppStore();

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-bg-border bg-bg-surface/80 px-4 py-6">
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-cyan/20">
          <div className="h-5 w-5 rounded-full border border-accent-cyan/70 bg-accent-cyan/30 shadow-[0_0_18px_rgba(0,212,255,0.8)]" />
        </div>
        <div>
          <div className="font-display text-lg tracking-wide text-text-primary">Pratyaksha</div>
          <div className="text-xs text-text-muted">Real-time deepfake detection</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 text-sm">
        {items.map((item) => {
          const active = pathname.startsWith(item.href);
          const isLive = item.href === "/verify/live" && isLiveActive;
          return (
            <Link key={item.href} href={item.href}>
              <div
                className={`group flex items-center gap-3 rounded-md px-3 py-2 transition-colors ${
                  active ? "border-l-2 border-accent-cyan bg-bg-border/60 text-accent-cyan" : "text-text-muted hover:bg-bg-border/40"
                }`}
              >
                <item.icon className="h-4 w-4" />
                <span className="font-medium">{item.label}</span>
                {isLive && (
                  <span className="ml-auto h-2 w-2 rounded-full bg-safe shadow-[0_0_12px_rgba(16,185,129,0.9)]" />
                )}
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="mt-6 border-t border-bg-border pt-4 text-xs text-text-muted">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-bg-border text-sm font-mono">
            {user?.email?.[0]?.toUpperCase() ?? "P"}
          </div>
          <div className="flex-1">
            <div className="truncate text-text-primary text-sm">{user?.email ?? "Analyst"}</div>
            <div className="mt-0.5 inline-flex items-center rounded-full bg-bg-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-accent-cyan">
              {user?.role ?? "verifier"}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

