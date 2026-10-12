/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Google Cloud Console'daki OAuth istemci kimliği; derleme sırasında gömülür. */
  readonly VITE_GOOGLE_CLIENT_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
