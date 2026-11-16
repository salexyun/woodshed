import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import { api } from "../api";
import type { components } from "../api-schema";
import Session from "./Session";

vi.mock("../api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));

type Schemas = components["schemas"];
type Init = { path?: Record<string, string | number>; body?: unknown };
type Call = Mock<(path: string, init?: Init) => Promise<unknown>>;

const get = api.get as unknown as Call;
const post = api.post as unknown as Call;

const SESSION_ID = 7;
const CARD = "Play it up an octave.";

const reviewsThenLesson: Schemas["Plan"] = {
  id: SESSION_ID,
  steps: [
    { kind: "review", id: "shape:minor:1", root: "F♯", card: null },
    { kind: "review", id: "shape:major:2", root: "B♭", card: null },
    { kind: "lesson", id: "diminished", card: CARD, root: null },
  ],
};

const standalonePassage: Schemas["Plan"] = {
  id: SESSION_ID,
  steps: [
    { kind: "passage", id: "passage:let-it-be", card: null, root: null },
    { kind: "challenge", id: "passage:let-it-be", card: "Same chords, reggae offbeat strum.", root: null },
  ],
};

const lesson: Schemas["Lesson"] = {
  quality: "diminished",
  explanation: "A diminished triad is a minor triad with the 5th lowered.",
  shapes: [
    [5, 4, 2],
    [8, 7, 8],
    [11, 13, 11],
  ],
  passages: ["passing-diminished"],
};

const passages: Record<string, Schemas["Passage"]> = {
  "passing-diminished": {
    id: "passing-diminished",
    title: "Passing diminished",
    artist: null,
    kind: "exercise",
    chords: ["C", "C♯°", "Dm", "G"],
    lesson: "diminished",
    unlocked: false,
  },
  "let-it-be": {
    id: "let-it-be",
    title: "Let It Be",
    artist: "The Beatles",
    kind: "song",
    chords: ["C", "G", "Am", "F"],
    lesson: "minor",
    unlocked: true,
  },
};

const FULL_SESSION_ITEMS = [
  "shape:minor:1",
  "shape:major:2",
  "shape:diminished:0",
  "shape:diminished:1",
  "shape:diminished:2",
  "passage:passing-diminished",
];

const summary: Schemas["Summary"] = {
  duration_seconds: 1505,
  items_rated: 6,
  next_due: FULL_SESSION_ITEMS.map((id) => ({ id, box: 2, due_at: "2026-11-19T09:00:00Z" })),
  streak: 5,
};

const ok = (data: unknown) => Promise.resolve({ ok: true, data });
const notFound = () =>
  Promise.resolve({ ok: false, error: { kind: "http", status: 404, detail: "not mocked" } });

function mockApi(plan: Schemas["Plan"]) {
  post.mockImplementation((path, init) => {
    if (init?.path?.id !== plan.id) return notFound();
    if (path === "/api/sessions/{id}/ratings")
      return ok({ id: "x", box: 2, due_at: "2026-11-19T09:00:00Z" });
    if (path === "/api/sessions/{id}/finish") return ok(summary);
    return notFound();
  });
  get.mockImplementation((path, init) => {
    // Shape reviews load their quality's lesson for the shape; the diminished content stands in for all.
    if (path === "/api/lessons/{quality}") return ok({ ...lesson, quality: init?.path?.quality });
    const passage = path === "/api/passages/{id}" && passages[String(init?.path?.id)];
    return passage ? ok(passage) : notFound();
  });
}

const callsTo = (path: string) => post.mock.calls.filter(([p]) => p === path);
const ratedItems = () =>
  callsTo("/api/sessions/{id}/ratings").map(([, init]) => (init?.body as Schemas["NewRating"]).item_id);

const button = (name: RegExp) => screen.findAllByRole("button", { name }).then((all) => all[0]);
const reveal = async () => fireEvent.click(await button(/reveal/i));
const next = async () => fireEvent.click(await button(/^(next|finish)$/i));

// Waits for the rated buttons to leave, so the next rating can't hit the same item twice.
async function rate(rating: Schemas["NewRating"]["rating"] = "easy") {
  const clicked = await button(new RegExp(`^${rating}$`, "i"));
  fireEvent.click(clicked);
  await waitFor(() => expect(clicked.isConnected).toBe(false));
}

const reviewFirstCard = async () => (await reveal(), rate());

async function playThroughLesson() {
  await reviewFirstCard();
  await reviewFirstCard();
  for (let i = 0; i < 3; i++) await rate();
  await rate();
}

let plan = reviewsThenLesson;

// Home posts /api/sessions and navigates here with the plan, since no endpoint
// returns a started session's plan yet (see #20).
const start = ({ length = "25" }: { length?: Schemas["NewSession"]["length"] } = {}) =>
  render(
    <MemoryRouter initialEntries={[{ pathname: `/sessions/${SESSION_ID}`, state: { plan, length } }]}>
      <Routes>
        <Route path="/sessions/:id" element={<Session />} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  plan = reviewsThenLesson;
  mockApi(plan);
});

describe("Timer", () => {
  it.each([
    ["25", "25:00"],
    ["open", "00:00"],
  ] as const)("shows the timer for the %s length", async (length, shown) => {
    start({ length });

    expect((await screen.findByRole("timer")).textContent).toBe(shown);
  });
});

describe("Review cards", () => {
  it("prompts the first review from the plan, with the answer hidden", async () => {
    start();

    await screen.findByText("Play F♯ minor, 1st inversion, on G-B-E");
    expect(screen.queryByRole("button", { name: /^easy$/i })).toBeNull();
  });

  it("posts each rating as it happens", async () => {
    start();
    await reveal();

    fireEvent.click(await button(/^challenging$/i));

    await waitFor(() =>
      expect(callsTo("/api/sessions/{id}/ratings")).toEqual([
        [
          "/api/sessions/{id}/ratings",
          { path: { id: SESSION_ID }, body: { item_id: "shape:minor:1", rating: "challenging" } },
        ],
      ]),
    );
    expect(callsTo("/api/sessions/{id}/finish")).toEqual([]);
  });

  it("renders the next card unrevealed after a rating", async () => {
    start();
    await reviewFirstCard();

    await screen.findByText("Play B♭ major, 2nd inversion, on G-B-E");
    screen.getByRole("button", { name: /reveal/i });
    expect(screen.queryByRole("button", { name: /^easy$/i })).toBeNull();
  });
});

describe("Lesson", () => {
  it("shows the explanation and the 3 shape diagrams after the reviews", async () => {
    start();
    await reviewFirstCard();
    await reviewFirstCard();

    await screen.findByText(lesson.explanation);
    expect(screen.getAllByRole("img", { name: "Fretboard" })).toHaveLength(3);
  });

  it("rates each of its 3 shapes, then its passage", async () => {
    start();

    await playThroughLesson();

    expect(ratedItems()).toEqual(FULL_SESSION_ITEMS);
  });

  it("shows its passage after the shapes and its challenge card after the passage", async () => {
    start();
    await reviewFirstCard();
    await reviewFirstCard();
    for (let i = 0; i < 3; i++) await rate();

    await screen.findByRole("heading", { name: "Passing diminished" });
    expect(screen.queryByText(CARD)).toBeNull();
    await rate();
    await screen.findByText(CARD);
  });
});

describe("Standalone passage", () => {
  beforeEach(() => {
    plan = standalonePassage;
    mockApi(plan);
  });

  it("rates the passage, then shows its challenge card", async () => {
    start();

    await screen.findByRole("heading", { name: "Let It Be" });
    await rate("unfamiliar");

    await screen.findByText("Same chords, reggae offbeat strum.");
    expect(ratedItems()).toEqual(["passage:let-it-be"]);
  });
});

describe("Full session", () => {
  it("finishes after the last step and shows the summary", async () => {
    start();
    await playThroughLesson();
    expect(callsTo("/api/sessions/{id}/finish")).toEqual([]);

    await next();

    await screen.findByRole("heading", { name: /summary/i });
    expect(callsTo("/api/sessions/{id}/finish")).toEqual([
      ["/api/sessions/{id}/finish", { path: { id: SESSION_ID } }],
    ]);
    screen.getByText("25:05");
    screen.getByText(/6 items rated/i);
    screen.getByText(/5-day streak/i);
    expect(screen.getAllByRole("listitem")).toHaveLength(summary.next_due.length);
  });
});
