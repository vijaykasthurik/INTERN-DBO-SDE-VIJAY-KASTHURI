import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight, Lock, Mail, User as UserIcon } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Tabs } from "../components/ui/Tabs";
import { useAuthStore } from "../stores/authStore";

export const AuthPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const { login, register, isLoading } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/workspace";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!email || !password) {
      setFormError("Please fill in all required fields.");
      return;
    }

    try {
      if (activeTab === "login") {
        await login(email, password);
      } else {
        if (!fullName) {
          setFormError("Full name is required to create an account.");
          return;
        }
        await register(email, password, fullName);
      }
      navigate(from, { replace: true });
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Authentication failed");
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent-indigo/5 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-md relative z-10"
      >
        {/* Brand header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-24 bg-accent-gradient text-white shadow-soft-sm mb-4">
            <Sparkles className="w-6 h-6" />
          </div>
          <h1 className="text-3xl font-serif text-ink tracking-tight font-medium">
            Welcome to Lumen
          </h1>
          <p className="text-sm text-ink-muted mt-2">
            The autonomous AI Data Analyst for high-velocity teams.
          </p>
        </div>

        <Card className="shadow-soft-lg border-hairline backdrop-blur-sm bg-white/95">
          <CardHeader className="pb-4">
            <div className="flex justify-center mb-2">
              <Tabs
                tabs={[
                  { id: "login", label: "Sign In" },
                  { id: "register", label: "Create Account" },
                ]}
                activeTab={activeTab}
                onChange={(tab) => {
                  setActiveTab(tab);
                  setFormError(null);
                }}
              />
            </div>
            <CardTitle className="text-center text-lg mt-3">
              {activeTab === "login" ? "Sign in to your workspace" : "Get started with Lumen"}
            </CardTitle>
            <CardDescription className="text-center">
              {activeTab === "login"
                ? "Enter your credentials to access your datasets and models."
                : "Create an isolated tenant workspace in seconds."}
            </CardDescription>
          </CardHeader>

          <CardContent>
            {formError && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 mb-4 text-xs text-rose-600 bg-rose-50 border border-rose-100 rounded-16"
              >
                {formError}
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {activeTab === "register" && (
                <Input
                  label="Full Name"
                  placeholder="Ada Lovelace"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  leftIcon={<UserIcon className="w-4 h-4 text-ink-muted" />}
                  required
                />
              )}

              <Input
                label="Work Email"
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail className="w-4 h-4 text-ink-muted" />}
                required
              />

              <Input
                label="Password"
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                leftIcon={<Lock className="w-4 h-4 text-ink-muted" />}
                required
              />

              <Button
                type="submit"
                className="w-full mt-2"
                size="lg"
                isLoading={isLoading}
              >
                <span>{activeTab === "login" ? "Sign In" : "Create Account"}</span>
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer info */}
        <p className="text-center text-xs text-ink-muted mt-6">
          Protected by tenant-isolated DuckDB sandboxes and deterministic LLM guardrails.
        </p>
      </motion.div>
    </div>
  );
};
