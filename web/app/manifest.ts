import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Consorcio Transparente",
    short_name: "Consorcio",
    description: "Panel de expensas del consorcio: liquidaciones, hallazgos e informes.",
    start_url: "/",
    display: "standalone",
    background_color: "#FFFFFF",
    theme_color: "#123A5C",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
    ],
  };
}
