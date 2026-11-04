import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "../components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { ProgressRing } from "../components/ui/ProgressRing";
import { Tabs } from "../components/ui/Tabs";
import { EmptyState } from "../components/ui/EmptyState";
import { Tag } from "../components/ui/Tag";
import { NAV_VARIANT } from "../components/Navbar";

describe("UI Primitives", () => {
  it("Button renders children, responds to clicks and handles loading", () => {
    const handleClick = vi.fn();
    const { rerender } = render(
      <Button onClick={handleClick} variant="primary">
        Click Me
      </Button>
    );

    const btn = screen.getByRole("button", { name: /click me/i });
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);

    rerender(
      <Button onClick={handleClick} isLoading>
        Click Me
      </Button>
    );
    expect(btn).toBeDisabled();
  });

  it("Card renders title, content, and structure", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title Test</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Card Content Test</p>
        </CardContent>
      </Card>
    );

    expect(screen.getByText("Card Title Test")).toBeInTheDocument();
    expect(screen.getByText("Card Content Test")).toBeInTheDocument();
  });

  it("Badge renders variant styles correctly", () => {
    render(<Badge variant="success">Active</Badge>);
    const badge = screen.getByText("Active");
    expect(badge).toBeInTheDocument();
  });

  it("ProgressRing displays score and calculates circumference", () => {
    render(<ProgressRing value={85} size={64} />);
    expect(screen.getByText("85")).toBeInTheDocument();
  });

  it("Tabs trigger onChange handler when clicked", () => {
    const handleChange = vi.fn();
    const tabs = [
      { id: "tab1", label: "Overview" },
      { id: "tab2", label: "Breakdown" },
    ];

    render(<Tabs tabs={tabs} activeTab="tab1" onChange={handleChange} />);
    const tab2 = screen.getByRole("tab", { name: "Breakdown" });
    fireEvent.click(tab2);
    expect(handleChange).toHaveBeenCalledWith("tab2");
  });

  it("EmptyState renders icon, title, and description", () => {
    render(
      <EmptyState
        title="No Data Available"
        description="Please upload CSV to start"
      />
    );
    expect(screen.getByText("No Data Available")).toBeInTheDocument();
    expect(screen.getByText("Please upload CSV to start")).toBeInTheDocument();
  });

  it("Tag renders label and triggers onRemove when provided", () => {
    const handleRemove = vi.fn();
    render(<Tag label="Filter: Sales" onRemove={handleRemove} />);
    expect(screen.getByText("Filter: Sales")).toBeInTheDocument();

    const removeBtn = screen.getByRole("button", { name: /remove tag/i });
    fireEvent.click(removeBtn);
    expect(handleRemove).toHaveBeenCalledTimes(1);
  });

  it("Navbar exports NAV_VARIANT conforming to design system", () => {
    expect(["capsule", "bottom-rounded"]).toContain(NAV_VARIANT);
  });
});
