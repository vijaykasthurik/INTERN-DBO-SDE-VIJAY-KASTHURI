import { create } from "zustand";
import {
  api,
  type ProviderCatalogEntry,
  type UserApiKeyResponse,
  type SharedPoolStatus,
} from "../lib/api";

interface AIConnectionState {
  connection: UserApiKeyResponse | null;
  sharedPool: SharedPoolStatus | null;
  catalog: ProviderCatalogEntry[];
  isConnectModalOpen: boolean;
  selectedProviderId: string | null;
  isLoading: boolean;
  error: string | null;

  fetchConnection: () => Promise<void>;
  fetchCatalog: () => Promise<void>;
  fetchSharedStatus: () => Promise<void>;
  openConnectModal: (providerId?: string) => void;
  closeConnectModal: () => void;
  setFallbackPreference: (allow: boolean) => Promise<void>;
}

export const useAIConnectionStore = create<AIConnectionState>((set, get) => ({
  connection: null,
  sharedPool: null,
  catalog: [],
  isConnectModalOpen: false,
  selectedProviderId: null,
  isLoading: false,
  error: null,

  fetchConnection: async () => {
    try {
      const data = await api.byok.getConnection();
      set({ connection: data, error: null });
    } catch {
      // Ignored if unauthenticated or error
    }
  },

  fetchCatalog: async () => {
    try {
      const catalog = await api.byok.catalog();
      set({ catalog });
    } catch (err: unknown) {
      console.warn("Failed to load providers catalog", err);
    }
  },

  fetchSharedStatus: async () => {
    try {
      const status = await api.byok.sharedStatus();
      set({ sharedPool: status });
    } catch (err: unknown) {
      console.warn("Failed to load shared pool status", err);
    }
  },

  openConnectModal: (providerId?: string) => {
    set({
      isConnectModalOpen: true,
      selectedProviderId: providerId || get().connection?.provider_id || "openai",
    });
  },

  closeConnectModal: () => {
    set({ isConnectModalOpen: false });
  },

  setFallbackPreference: async (allow: boolean) => {
    try {
      await api.byok.update({ allow_shared_fallback: allow });
      const current = get().connection;
      if (current) {
        set({ connection: { ...current, allow_shared_fallback: allow } });
      }
    } catch (err: unknown) {
      console.error("Failed to update fallback preference", err);
    }
  },
}));
