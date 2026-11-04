import { create } from "zustand";
import { api, type Dataset, type Relationship } from "../lib/api";

interface DatasetState {
  datasets: Dataset[];
  selectedDataset: Dataset | null;
  relationships: Relationship[];
  isLoading: boolean;
  error: string | null;
  fetchDatasets: () => Promise<void>;
  selectDataset: (id: string | number) => Promise<void>;
  uploadFiles: (files: File[]) => Promise<Dataset[]>;
  deleteDataset: (id: string | number) => Promise<void>;
}

export const useDatasetStore = create<DatasetState>((set, get) => ({
  datasets: [],
  selectedDataset: null,
  relationships: [],
  isLoading: false,
  error: null,

  fetchDatasets: async () => {
    set({ isLoading: true, error: null });
    try {
      const datasets = await api.datasets.list();
      set({ datasets, isLoading: false });
      if (datasets.length > 0 && !get().selectedDataset) {
        await get().selectDataset(datasets[0].id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load datasets";
      set({ isLoading: false, error: msg });
    }
  },

  selectDataset: async (id: string | number) => {
    set({ isLoading: true, error: null });
    try {
      const [dataset, rels] = await Promise.all([
        api.datasets.get(id),
        api.datasets.relationships().catch(() => []),
      ]);
      set({ selectedDataset: dataset, relationships: rels, isLoading: false });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to fetch dataset details";
      set({ isLoading: false, error: msg });
    }
  },

  uploadFiles: async (files: File[]) => {
    set({ isLoading: true, error: null });
    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      const res = await api.datasets.upload(formData);
      await get().fetchDatasets();
      const uploaded = res.datasets || [];
      if (uploaded.length > 0) {
        await get().selectDataset(uploaded[0].id);
      }
      return uploaded;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload files";
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  deleteDataset: async (id: string | number) => {
    set({ isLoading: true, error: null });
    try {
      await api.datasets.delete(id);
      const remaining = get().datasets.filter((d) => d.id !== id);
      set({
        datasets: remaining,
        selectedDataset: remaining.length > 0 ? remaining[0] : null,
        isLoading: false,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete dataset";
      set({ isLoading: false, error: msg });
      throw err;
    }
  },
}));
