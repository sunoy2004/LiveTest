import * as React from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Eye, EyeOff } from "lucide-react";

export function LoginPage() {
  const { login, token, isReady } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [pending, setPending] = React.useState(false);

  if (!isReady) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (token) {
    return <Navigate to={from} replace />;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const u = await login(email, password);
      if (u.is_admin) {
        navigate("/mentoring/admin/mentors", { replace: true });
      } else {
        navigate(from, { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex min-h-svh w-full items-center justify-center bg-[radial-gradient(circle_at_top_left,_var(--tw-gradient-stops))] from-slate-900 via-indigo-950 to-slate-950 p-6 animate-in fade-in duration-1000">
      {/* Ambient background glow */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="relative w-full max-w-sm space-y-8 rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl p-10 shadow-2xl shadow-black/50 animate-in zoom-in-95 duration-500">
        <div className="space-y-2 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/20 mb-6 rotate-3 hover:rotate-0 transition-transform duration-300">
            <Sparkles className="h-7 w-7" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Welcome Back</h1>
          <p className="text-sm text-slate-400">Securely sign in to your dashboard</p>
        </div>
        
        <form onSubmit={onSubmit} className="space-y-6">
          <div className="space-y-2">
            <label htmlFor="email" className="text-xs font-semibold uppercase tracking-widest text-slate-500 ml-1">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex h-12 w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white placeholder:text-slate-600 transition-all focus:border-indigo-500 focus:bg-white/10 focus:ring-4 focus:ring-indigo-500/10 outline-none"
              placeholder="name@example.com"
            />
          </div>
          
          <div className="space-y-2">
            <label htmlFor="password" className="text-xs font-semibold uppercase tracking-widest text-slate-500 ml-1">
              Password
            </label>
            <div className="relative group">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="flex h-12 w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white placeholder:text-slate-600 transition-all focus:border-indigo-500 focus:bg-white/10 focus:ring-4 focus:ring-indigo-500/10 outline-none pr-12"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors p-2 rounded-lg hover:bg-white/5"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-4 animate-in slide-in-from-top-2 duration-300">
              <p className="text-xs font-medium text-red-400">{error}</p>
            </div>
          )}

          <Button 
            type="submit" 
            className="w-full h-12 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-bold text-sm shadow-xl shadow-indigo-500/20 transition-all active:scale-[0.98] disabled:opacity-50 border-0" 
            disabled={pending}
          >
            {pending ? (
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                <span>Processing...</span>
              </div>
            ) : (
              "Sign In"
            )}
          </Button>
        </form>
        
        <div className="pt-2 text-center">
          <p className="text-[10px] uppercase tracking-widest text-slate-600 font-medium">
            Protected by Antigravity v1.0
          </p>
        </div>
      </div>
    </div>
  );
}

import { Sparkles } from "lucide-react";
