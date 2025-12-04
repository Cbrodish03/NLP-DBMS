import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],

  server: {
    host: true, // allows external access
    allowedHosts: ["nlp.discovery.cs.vt.edu"], // allow your CS Launch hostname
    port: 5173, // matches your docker-compose internal port
  },
});
