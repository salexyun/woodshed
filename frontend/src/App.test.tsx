import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, vi } from "vitest";

import type { components } from "./api-schema";
import App from "./App";

const HOME: components["schemas"]["Home"] = {
  streak: 6,
  week_days: 2,
  weekly_goal_days: 4,
  due_count: 3,
  next_lesson: "minor",
  cue: "after coffee",
};

vi.mock("./api", () => ({
  api: { get: async (path: string) => ({ ok: true, data: path === "/api/home" ? HOME : {} }) },
}));

describe("App", () => {
  it("renders Home at / once onboarded", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    await screen.findByRole("button", { name: "Today's plan" });
    await screen.findByText(/6.day streak/i);
  });
});
