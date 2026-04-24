import { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
}

const SectionCard = ({ title, subtitle, children, action }: SectionCardProps) => {
  return (
    <div className="bg-card rounded-2xl p-6 shadow-card border border-border hover:shadow-card-hover transition-all duration-300 animate-fade-in">
      <div className="flex items-start justify-between mb-5">
        <div>
          <h2 className="text-base font-semibold text-foreground tracking-tight">{title}</h2>
          {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
        </div>
        {action && <div className="flex items-center gap-2">{action}</div>}
      </div>
      {children}
    </div>
  );
};

export default SectionCard;
