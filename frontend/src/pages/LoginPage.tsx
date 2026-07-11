import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "@/api/endpoints";
import { useAuth } from "@/auth/AuthContext";
import { ApiError } from "@/api/client";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { setAuthenticated } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      setAuthenticated(true);
      navigate("/dashboard");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Unable to sign in.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-ink-50 to-white px-4">
      <div className="w-full max-w-[380px]">
        <div className="flex items-center gap-2.5 mb-8 justify-center">
          <div className="w-8 h-8 rounded-lg bg-ink-900 flex items-center justify-center">
            <span className="text-white text-xs font-semibold tracking-tight">TP</span>
          </div>
          <span className="text-sm font-medium text-ink-700 tracking-tight">
            Timesheet Processor
          </span>
        </div>

        <div className="bg-white rounded-2xl shadow-card border border-ink-100 px-8 py-9">
          <h1 className="text-lg font-semibold text-ink-900 tracking-tight mb-1">
            Sign in
          </h1>
          <p className="text-sm text-ink-400 mb-7">
            Enter your credentials to continue
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-ink-600 mb-1.5 tracking-tight">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg border border-ink-200 bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-300 transition-colors duration-150 focus:outline-none focus:border-accent-500 focus:ring-4 focus:ring-accent-500/10"
                autoComplete="username"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-ink-600 mb-1.5 tracking-tight">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-ink-200 bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-300 transition-colors duration-150 focus:outline-none focus:border-accent-500 focus:ring-4 focus:ring-accent-500/10"
                autoComplete="current-password"
                required
              />
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-100 px-3.5 py-2.5">
                <p className="text-xs text-red-600 font-medium">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-ink-900 text-white text-sm font-medium py-2.5 mt-2 transition-all duration-150 hover:bg-ink-800 active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 shadow-sm"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-ink-300 mt-6">
          Single admin account · No self-registration
        </p>
      </div>
    </div>
  );
}