import { render, screen } from "@testing-library/react";
import { RolProvider, useRol } from "@/components/rol-context";

function Sonda() {
  return <p>rol: {useRol()}</p>;
}

test("useRol devuelve el rol del provider", () => {
  render(
    <RolProvider rol="consejo">
      <Sonda />
    </RolProvider>
  );
  expect(screen.getByText("rol: consejo")).toBeInTheDocument();
});

test("sin provider, useRol asume auditor (los tests existentes renderizan sin provider)", () => {
  render(<Sonda />);
  expect(screen.getByText("rol: auditor")).toBeInTheDocument();
});
