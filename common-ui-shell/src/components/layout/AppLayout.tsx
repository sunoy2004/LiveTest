import { Outlet } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

export function AppLayout() {
  return (
    <TooltipProvider delayDuration={0}>
      <div
        data-cui-shell
        className="flex h-svh min-h-0 w-full overflow-hidden bg-background"
      >
        <AppSidebar />
        <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <Outlet />
        </div>
      </div>
    </TooltipProvider>
  );
}
