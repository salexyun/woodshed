import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../api-schema";
import Home from "./Home";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("../api", () => ({ api: { get, post, patch: vi.fn() } }));

const home: components["schemas"]["Home"] = {
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

const PLAN = { id: 7, steps: [] };
const START_BUTTONS = ACTIONS.map(([label]) => label);

function Location() {
  const { pathname, search, state } = useLocation();
  return (
    <>
      <p data-testid="location">{pathname + search}</p>
      <p data-testid="state">{JSON.stringify(state)}</p>
    </>
  );
}

function renderHome(data: Partial<typeof home> = {}) {
  get.mockImplementation(async (path: string) =>
    path === "/api/home" ? { ok: true, data: { ...home, ...data } } : { ok: false, error: { kind: "network" } },
  );
  renderScreen();
}

function renderScreen() {
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
const routerState = async () => JSON.parse((await screen.findByTestId("state")).textContent!);
const button = (name: string) => screen.queryByRole<HTMLButtonElement>("button", { name });
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
    renderHome({ next_lesson: null });
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
      post.mockResolvedValue({ ok: true, data: PLAN });
      renderHome();

      await choose(label, length);

      expect(post).toHaveBeenCalledExactlyOnceWith("/api/sessions", { body: { action, length: value } });
      expect(await location()).toBe("/sessions/7");
      expect(await routerState()).toEqual({ plan: PLAN, length: value });
    },
  );

  it.each(LENGTHS)("sends Pick a song to its screen with length %s instead of starting a session", async (length, value) => {
    renderHome();

    await choose("Pick a song", length);

    expect(await location()).toBe(`/pick-a-song?length=${value}`);
    expect(post).not.toHaveBeenCalled();
  });

  it("hides or disables Continue when there is no next lesson", async () => {
    renderHome({ next_lesson: null });
    await screen.findByText(/all lessons done/i);

    const continueButton = button("Continue");
    expect(continueButton === null || continueButton.disabled).toBe(true);
  });

  it("enables Continue when there is a next lesson", async () => {
    renderHome();
    await screen.findByText(/next lesson: minor/i);

    expect(button("Continue")!.disabled).toBe(false);
  });

  it.each(START_BUTTONS)("disables the start buttons while %s is starting, so a double tap posts once", async (label) => {
    let resolve!: (result: unknown) => void;
    post.mockReturnValue(new Promise((r) => (resolve = r)));
    renderHome();
    await screen.findByText(/next lesson: minor/i);

    fireEvent.click(button(label)!);
    fireEvent.click(button(label)!);

    await waitFor(() => START_BUTTONS.forEach((name) => expect(button(name)!.disabled).toBe(true)));
    expect(post).toHaveBeenCalledTimes(1);
    resolve({ ok: true, data: PLAN });
    expect(await location()).toBe("/sessions/7");
  });

  it("shows the alert and stays on Home when starting a session fails", async () => {
    post.mockResolvedValue({ ok: false, error: { kind: "http", status: 500 } });
    renderHome();

    await choose("Today's plan", /25 min/i);

    await screen.findByRole("alert");
    expect(screen.queryByTestId("location")).toBeNull();
    // The alert says "Try again", so the buttons must work again.
    START_BUTTONS.forEach((name) => expect(button(name)!.disabled).toBe(false));
  });

  it.each([
    ["still loading", () => new Promise(() => {})],
    ["failed to load", async () => ({ ok: false, error: { kind: "network" } })],
  ])("explains a 409 from Continue when every lesson is done and Home %s", async (_, getHome) => {
    get.mockImplementation(getHome);
    post.mockResolvedValue({ ok: false, error: { kind: "http", status: 409, detail: "no next lesson" } });
    renderScreen();

    fireEvent.click(button("Continue")!);

    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/lessons/i));
    expect(screen.queryByText(/couldn't reach the server/i)).toBeNull();
    expect(screen.queryByTestId("location")).toBeNull();
  });

  it("explains a 409 from Test me when there is nothing to test yet", async () => {
    post.mockResolvedValue({ ok: false, error: { kind: "http", status: 409, detail: "nothing to test" } });
    renderHome();
    await screen.findByText(/next lesson: minor/i);

    fireEvent.click(button("Test me")!);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/nothing to test/i);
    expect(alert.textContent).not.toMatch(/continue|couldn't reach the server/i);
    expect(screen.queryByTestId("location")).toBeNull();
    START_BUTTONS.forEach((name) => expect(button(name)!.disabled).toBe(false));
  });
});
