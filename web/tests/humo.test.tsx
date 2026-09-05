import { render, screen } from "@testing-library/react";

function Hola() {
  return <h1>Consorcio Transparente</h1>;
}

test("el entorno de tests renderiza React", () => {
  render(<Hola />);
  expect(screen.getByText("Consorcio Transparente")).toBeInTheDocument();
});
