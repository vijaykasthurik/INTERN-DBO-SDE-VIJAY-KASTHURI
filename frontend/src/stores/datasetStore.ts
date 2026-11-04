import { create } from "zustand";
import { api, type Dataset, type Relationship } from "../lib/api";

interface DatasetState {
  datasets: Dataset[];
  selectedDataset: Dataset | null;
  relationships: Relationship[];
  isLoading: boolean;
  error: string | null;
  uploadWarnings: string[];
  fetchDatasets: () => Promise<void>;
  selectDataset: (id: string | number) => Promise<void>;
  uploadFiles: (files: File[], onProgress?: (filename:string, percent:number) => void) => Promise<Dataset[]>;
  deleteDataset: (id: string | number) => Promise<void>;
}

export const useDatasetStore = create<DatasetState>((set, get) => ({
  datasets: [],
  selectedDataset: null,
  relationships: [],
  isLoading: false,
  error: null,
  uploadWarnings: [],

  fetchDatasets: async () => {
    set({ isLoading: true, error: null });
    try {
      const datasets = await api.datasets.list();
      const selectedId = get().selectedDataset?.id;
      const selectionExists = datasets.some((dataset) => dataset.id === selectedId);
      set({ datasets, isLoading: false, selectedDataset: selectionExists ? get().selectedDataset : null });
      if (datasets.length > 0 && !selectionExists) {
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

  uploadFiles: async (files, onProgress) => {
    set({isLoading:true,error:null,uploadWarnings:[]});
    const uploaded:Dataset[]=[]; const warnings:string[]=[];
    for(const file of files) {
      const data = new FormData(); data.append("files",file);
      try { const result=await api.datasets.upload(data,(percent)=>onProgress?.(file.name,percent)); uploaded.push(...result.datasets); warnings.push(...(result.errors||[]).map(item=>`${item.file}: ${item.error}`)); }
      catch(err) { warnings.push(`${file.name}: ${err instanceof Error?err.message:"Upload failed"}`); }
    }
    await get().fetchDatasets();
    set({isLoading:false,uploadWarnings:warnings,error:uploaded.length?null:warnings.join("; ")});
    if(!uploaded.length) throw new Error(warnings.join("; "));
    return uploaded;
  },

  deleteDataset: async (id: string | number) => {
    set({ isLoading: true, error: null });
    try {
      await api.datasets.delete(id);
      const remaining = get().datasets.filter((d) => d.id !== id);
      set({
        datasets: remaining,
        selectedDataset: null,
        isLoading: false,
      });
      if (remaining.length > 0) await get().selectDataset(remaining[0].id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete dataset";
      set({ isLoading: false, error: msg });
      throw err;
    }
  },
}));
