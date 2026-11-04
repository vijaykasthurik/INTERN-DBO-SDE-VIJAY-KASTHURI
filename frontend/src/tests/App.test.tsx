import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App, { NAV_VARIANT } from "../App.tsx";

describe("App Component", () => {
  it("renders the brand header and navbar", () => {
    render(<App />);
    expect(screen.getByText("Lumen")).toBeInTheDocument();
    expect(screen.getByText("Launch Studio")).toBeInTheDocument();
  });

  it("exports NAV_VARIANT constant conforming to design system", () => {
    expect(["capsule", "bottom-rounded"]).toContain(NAV_VARIANT);
  });

  it("renders the hero headline and ground truth value proposition", () => {
    render(<App />);
    expect(screen.getByText(/Chat with datasets/i)).toBeInTheDocument();
    expect(screen.getByText(/Ground truth/i)).toBeInTheDocument();
    expect(screen.getByText("Upload Your CSV")).toBeInTheDocument();
  });

  it("renders the live preview card with verifier indicator", () => {
    render(<App />);
    expect(screen.getByText(/Verifier: High Confidence/i)).toBeInTheDocument();
    expect(screen.getByText(/sales_q3_actuals.duckdb/i)).toBeInTheDocument();
  });
});
