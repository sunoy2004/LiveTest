/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USER_SERVICE_URL?: string;
  readonly VITE_MFE_REMOTE_PORT?: string;
  readonly VITE_MENTOR_REMOTE_ENTRY?: string;
  readonly VITE_MENTORING_API_BASE_URL?: string;
  readonly VITE_GAMIFICATION_SERVICE_URL?: string;
  readonly VITE_AI_API_BASE_URL?: string;
}

declare module "mentorMentee/App" {
  import type { FC } from "react";

  type ShellUser = {
    id: string;
    email: string;
    is_admin?: boolean;
  };

  const App: FC<{
    embedded?: boolean;
    basename?: string;
    shellUser?: ShellUser | null;
    shellToken?: string | null;
  }>;
  export default App;
}
