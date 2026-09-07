import type { Metadata } from "next";
import { Lexend, Source_Sans_3 } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const lexend = Lexend({ subsets: ["latin"], variable: "--font-titulos" });
const sourceSans = Source_Sans_3({ subsets: ["latin"], variable: "--font-cuerpo" });

// Título neutro: cada sección pone el suyo en su layout ("Hallazgos — Consorcio Transparente").
export const metadata: Metadata = {
  title: "Consorcio Transparente",
  description: "Panel de auditoría de expensas del Consorcio Rivadavia 2069",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-AR">
      <body className={`${lexend.variable} ${sourceSans.variable} font-cuerpo bg-fondo text-tinta antialiased`}>
        {children}
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
