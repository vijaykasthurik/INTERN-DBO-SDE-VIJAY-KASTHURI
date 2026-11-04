import { create } from "zustand";
import { api, type User } from "../lib/api";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  checkAuth: () => Promise<void>;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string, name: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem("lumen_access_token"),
  isLoading: true,
  error: null,

  checkAuth: async () => {
    const token = localStorage.getItem("lumen_access_token");
    if (!token) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }
    try {
      const user = await api.auth.me();
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch {
      api.auth.logout();
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      await api.auth.login({ email, password });
      const user = await api.auth.me();
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to sign in";
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  register: async (email, password, full_name) => {
    set({ isLoading: true, error: null });
    try {
      await api.auth.register({ email, password, full_name });
      await api.auth.login({ email, password });
      const user = await api.auth.me();
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to register";
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  logout: () => {
    api.auth.logout();
    set({ user: null, isAuthenticated: false, error: null });
  },
}));
