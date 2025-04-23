declare module '@capacitor/storage' {
  export interface StoragePlugin {
    get(options: { key: string }): Promise<{ value: string | null }>;
    set(options: { key: string; value: string }): Promise<void>;
    remove(options: { key: string }): Promise<void>;
    clear(): Promise<void>;
    keys(): Promise<{ keys: string[] }>;
  }

  export const Storage: StoragePlugin;
} 