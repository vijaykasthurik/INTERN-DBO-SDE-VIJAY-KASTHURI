import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../App.tsx";
import { NAV_VARIANT } from "../components/Navbar.tsx";

describe("App Component", () => {
  it("renders the brand header and navbar links", () => {
    render(<App />);
    const lumenElements = screen.getAllByText("Lumen");
    expect(lumenElements.length).toBeGreaterThan(0);
    const workspaceLinks = screen.getAllByText("Workspace");
    expect(workspaceLinks.length).toBeGreaterThan(0);
  });

  it("exports NAV_VARIANT constant conforming to design system", () => {
    expect(["capsule", "bottom-rounded"]).toContain(NAV_VARIANT);
  });

  it("renders the hero headline and ground truth value proposition", async () => {
    render(<App />);
    expect(await screen.findByText(/Instant clarity from/i)).toBeInTheDocument();
    expect(await screen.findByText(/raw tabular data/i)).toBeInTheDocument();
  });

  it("renders the mini demo preview with verifier indicator", async () => {
    render(<App />);
    expect(await screen.findByText(/lumen:\/\/session-emea-analysis/i)).toBeInTheDocument();
  });
});
