import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import type { components } from "../api-schema";
import Progress from "./Progress";

vi.mock("../api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));

type Schemas = components["schemas"];

const DUE = "2026-11-20T09:00:00Z";
const PROGRESS: Schemas["ProgressItem"][] = [
  { id: "shape:major:0", box: 5, due_at: DUE },
  { id: "shape:major:1", box: 2, due_at: DUE },
  { id: "shape:minor:2", box: 1, due_at: DUE },
  { id: "passage:la-bamba", box: 3, due_at: DUE },
];

// Newest first, as the API returns them. 18:30 UTC is the next day in Seoul.
const SESSIONS: Schemas["PastSession"][] = [
  {
    id: 4,
    action: "continue",
    length: "25",
    started_at: "2026-11-15T09:00:00Z",
    items_rated: 0,
    duration_seconds: null,
  },
  {
    id: 3,
    action: "test_me",
    length: "25",
    started_at: "2026-11-15T08:00:00Z",
    items_rated: 1,
    duration_seconds: 20,
  },
  {
    id: 2,
    action: "pick_a_song",
    length: "25",
    started_at: "2026-11-14T18:30:00Z",
    items_rated: 3,
    duration_seconds: 1500,
  },
  {
    id: 1,
    action: "today",
    length: "open",
    started_at: "2026-11-13T10:00:00Z",
    items_rated: 5,
    duration_seconds: 2400,
  },
];

const PROFILE: Schemas["Profile"] = {
  years_playing: 3,
  stuck_on: "same_material",
  cue: "after coffee",
  weekly_goal_days: 4,
  timezone: "Asia/Seoul",
};

const DATA: Record<string, unknown> = {
  "/api/progress": PROGRESS,
  "/api/sessions": SESSIONS,
  "/api/profile": PROFILE,
};

function renderScreen() {
  vi.mocked(api.get).mockImplementation(async (path: string) => ({ ok: true, data: DATA[path] as never }));
  vi.mocked(api.patch).mockResolvedValue({ ok: true, data: PROFILE });
  render(<Progress />);
}

const shapeCell = (label: string) => screen.findByLabelText(new RegExp(`^${label}$`, "i"));

afterEach(() => vi.resetAllMocks());

describe("shape map", () => {
  it("shows the 12 shapes and no passages", async () => {
    renderScreen();

    await shapeCell("major, root position");
    const shapes = screen.getAllByLabelText(/^\w+, (root position|1st inversion|2nd inversion)$/i);
    expect(shapes).toHaveLength(12);
    expect(screen.queryByText(/la bamba/i)).toBeNull();
  });

  it.each([
    ["major, root position", "5"],
    ["major, 1st inversion", "2"],
    ["minor, 2nd inversion", "1"],
  ])("colors %s by box %s", async (label, box) => {
    renderScreen();

    expect((await shapeCell(label)).dataset.box).toBe(box);
  });

  it("leaves shapes without an item uncolored", async () => {
    renderScreen();

    expect((await shapeCell("augmented, 2nd inversion")).dataset.box).toBeUndefined();
  });
});

describe("history", () => {
  it("lists each session's date, duration, action and items, newest first", async () => {
    renderScreen();

    const table = await screen.findByRole("table", { name: /history/i });
    await within(table).findAllByText("2026-11-15");
    const rows = within(table)
      .getAllByRole("row")
      .filter((row) => within(row).queryAllByRole("cell").length)
      .map((row) => within(row).getAllByRole("cell").map((cell) => cell.textContent));
    expect(rows).toEqual([
      ["2026-11-15", "—", "Continue", "0 items"],
      ["2026-11-15", "<1 min", "Test me", "1 item"],
      ["2026-11-15", "25 min", "Pick a song", "3 items"],
      ["2026-11-13", "40 min", "Today's plan", "5 items"],
    ]);
  });
});

describe("settings", () => {
  it("shows the current cue and weekly goal", async () => {
    renderScreen();

    await waitFor(() =>
      expect(screen.getByLabelText<HTMLInputElement>(/cue/i).value).toBe("after coffee"),
    );
    expect(screen.getByLabelText<HTMLInputElement>(/weekly goal/i).value).toBe("4");
  });

  it("saves the cue and weekly goal to the profile", async () => {
    renderScreen();
    await waitFor(() =>
      expect(screen.getByLabelText<HTMLInputElement>(/cue/i).value).toBe("after coffee"),
    );

    fireEvent.change(screen.getByLabelText(/cue/i), { target: { value: "after dinner" } });
    fireEvent.change(screen.getByLabelText(/weekly goal/i), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith("/api/profile", {
        body: { cue: "after dinner", weekly_goal_days: 5 },
      }),
    );
  });

  it("shows the form only once the profile has loaded", async () => {
    vi.mocked(api.get).mockImplementation(async (path: string) =>
      path === "/api/profile" ? new Promise(() => {}) : { ok: true, data: DATA[path] as never },
    );
    render(<Progress />);

    await shapeCell("major, root position");
    expect(screen.queryByRole("button", { name: /save/i })).toBeNull();
  });

  it("shows a validation error when the save is rejected", async () => {
    renderScreen();
    vi.mocked(api.patch).mockResolvedValue({
      ok: false,
      error: { kind: "http", status: 422, detail: [] },
    });
    await waitFor(() =>
      expect(screen.getByLabelText<HTMLInputElement>(/cue/i).value).toBe("after coffee"),
    );

    fireEvent.change(screen.getByLabelText(/cue/i), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/goal is 1 to 7 days/);
  });

  it("shows a server error when the save fails otherwise", async () => {
    renderScreen();
    vi.mocked(api.patch).mockResolvedValue({ ok: false, error: { kind: "network" } });
    await waitFor(() =>
      expect(screen.getByLabelText<HTMLInputElement>(/cue/i).value).toBe("after coffee"),
    );

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/couldn't reach the server/i);
  });
});
