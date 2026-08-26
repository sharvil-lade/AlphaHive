"use client";

import React from "react";
import { cn } from "../../lib/utils";
import { ThemeToggle } from "../layout/ThemeToggle";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("bg-surface border border-surface-border rounded-lg p-4", className)}>
      {children}
    </div>
  );
}

export function Button({
  className,
  variant = "default",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "outline" | "ghost" | "danger" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-md text-sm font-medium px-3 py-1.5 transition-colors disabled:opacity-50 disabled:pointer-events-none",
        variant === "default" && "bg-foreground text-background hover:opacity-90",
        variant === "outline" && "border border-surface-border text-foreground hover:bg-surface-hover",
        variant === "ghost" && "text-mutedText hover:text-foreground hover:bg-surface-hover",
        variant === "danger" && "text-bearish hover:bg-bearish/10",
        className
      )}
      {...props}
    />
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        "bg-surface-raised border border-surface-border rounded-md px-3 py-1.5 text-sm placeholder:text-mutedText focus:border-mutedText transition-colors",
        props.className
      )}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(
        "bg-surface-raised border border-surface-border rounded-md px-3 py-1.5 text-sm focus:border-mutedText transition-colors",
        className
      )}
    >
      {children}
    </select>
  );
}

export function PageHeader({ title, description }: { title: string; description?: string }) {
  return (
    // pl-14 clears the fixed mobile menu button rendered by the Sidebar.
    <div className="h-14 shrink-0 border-b border-surface-border flex items-center justify-between pl-14 pr-4 md:px-6">
      <div>
        <h1 className="text-sm font-semibold">{title}</h1>
        {description && <p className="text-[11px] text-mutedText">{description}</p>}
      </div>
      <ThemeToggle />
    </div>
  );
}

export function Delta({ value, suffix = "%" }: { value: number; suffix?: string }) {
  const positive = value >= 0;
  return (
    <span className={cn("font-medium", positive ? "text-bullish" : "text-bearish")}>
      {positive ? "+" : ""}
      {value.toFixed(2)}
      {suffix}
    </span>
  );
}
