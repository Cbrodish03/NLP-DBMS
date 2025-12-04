import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],

  server: {
    host: true, // bind to 0.0.0.0 for container access
    // Allow localhost/127.0.0.1 for local dev plus the CS Launch hostname.
    allowedHosts: ["localhost", "127.0.0.1", "nlp.discovery.cs.vt.edu"],
    port: 5173, // matches your docker-compose internal port
  },
});
