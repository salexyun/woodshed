/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // Testing Library registers its afterEach cleanup only when globals are on.
  test: { environment: "jsdom", globals: true },
});
