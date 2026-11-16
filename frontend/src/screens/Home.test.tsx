import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Home from "./Home";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("../api", () => ({ api: { get, post, patch: vi.fn() } }));

const home = {
  streak: 6,
  week_days: 2,
  weekly_goal_days: 4,
  due_count: 3,
  next_lesson: "minor",
  cue: "after coffee",
};

const ACTIONS = [
  ["Today's plan", "today"],
  ["Continue", "continue"],
  ["Test me", "test_me"],
] as const;
const LENGTHS = [
  [/25 min/i, "25"],
  [/open-ended/i, "open"],
] as const;

function Location() {
  const { pathname, search } = useLocation();
  return <p data-testid="location">{pathname + search}</p>;
}

function renderHome(data: Partial<typeof home> = {}) {
  get.mockImplementation(async (path: string) =>
    path === "/api/home" ? { ok: true, data: { ...home, ...data } } : { ok: false, error: { kind: "network" } },
  );
  render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="*" element={<Location />} />
      </Routes>
    </MemoryRouter>,
  );
}

const location = async () => (await screen.findByTestId("location")).textContent;
const choose = async (action: string, length: RegExp) => {
  fireEvent.click(await screen.findByRole("radio", { name: length }));
  fireEvent.click(screen.getByRole("button", { name: action }));
};

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("Home", () => {
  it.each([
    ["streak", /6.day streak/i],
    ["weekly progress", /2 of 4 days this week/i],
    ["due count", /3 reviews due/i],
    ["next lesson", /next lesson: minor/i],
    ["cue", /after coffee/i],
  ])("shows the %s from GET /api/home", async (_, text) => {
    renderHome();
    await screen.findByText(text);
  });

  it("says all lessons are done when there is no next lesson", async () => {
    renderHome({ next_lesson: null as unknown as string });
    await screen.findByText(/all lessons done/i);
  });

  it("offers the 4 actions and the 2 lengths", async () => {
    renderHome();
    for (const name of ["Today's plan", "Continue", "Test me", "Pick a song"])
      await screen.findByRole("button", { name });
    for (const [name] of LENGTHS) screen.getByRole("radio", { name });
  });

  it.each(ACTIONS.flatMap(([label, action]) => LENGTHS.map(([length, value]) => [label, action, length, value] as const)))(
    "starts %s as %s with length %s",
    async (label, action, length, value) => {
      post.mockResolvedValue({ ok: true, data: { id: 7, steps: [] } });
      renderHome();

      await choose(label, length);

      expect(post).toHaveBeenCalledExactlyOnceWith("/api/sessions", { body: { action, length: value } });
      expect(await location()).toBe("/sessions/7");
    },
  );

  it.each(LENGTHS)("sends Pick a song to its screen with length %s instead of starting a session", async (length, value) => {
    renderHome();

    await choose("Pick a song", length);

    expect(await location()).toBe(`/pick-a-song?length=${value}`);
    expect(post).not.toHaveBeenCalled();
  });
});
