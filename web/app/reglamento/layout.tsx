// Las páginas de esta sección son client components: el título va en este
// layout de servidor (el patrón más simple del App Router para eso).
export const metadata = { title: "Reglamento — Consorcio Transparente" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
