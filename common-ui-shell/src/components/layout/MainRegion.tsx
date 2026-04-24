import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type MainRegionProps = {
  title: string;
  description?: string;
  children?: ReactNode;
  /** Full main column for embedded content (e.g. iframe) with no title chrome. */
  bare?: boolean;
};

/**
 * Standard main column: title bar + scrollable body.
 */
export function MainRegion({ title, description, children, bare }: MainRegionProps) {
  if (bare) {
    return <div className="flex min-h-0 flex-1 flex-col">{children}</div>;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 border-b border-border bg-card/40 px-6 py-4 backdrop-blur-sm">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        ) : null}
      </header>
      <div className="min-h-0 flex-1 overflow-auto p-6">{children}</div>
    </div>
  );
}
