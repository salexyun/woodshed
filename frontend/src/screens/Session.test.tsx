import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";

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

// A shape rated in an abandoned lesson comes due as a review before that lesson is complete.
const reviewThenItsLesson: Schemas["Plan"] = {
  id: SESSION_ID,
  steps: [
    { kind: "review", id: "shape:diminished:0", root: "A", card: null },
    { kind: "review", id: "shape:major:0", root: "C", card: null },
    { kind: "review", id: "shape:minor:1", root: "F♯", card: null },
    { kind: "lesson", id: "diminished", card: CARD, root: null },
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
const failure = (status: number) =>
  Promise.resolve({ ok: false, error: { kind: "http", status, detail: "mocked failure" } });
const notFound = () => failure(404);

function mockApi(plan: Schemas["Plan"], { rated = [] as string[], finished_at = null as string | null } = {}) {
  post.mockImplementation((path, init) => {
    if (init?.path?.id !== plan.id) return notFound();
    if (path === "/api/sessions/{id}/ratings")
      return ok({ id: "x", box: 2, due_at: "2026-11-19T09:00:00Z" });
    if (path === "/api/sessions/{id}/finish") return ok(summary);
    return notFound();
  });
  get.mockImplementation((path, init) => {
    if (path === "/api/sessions/{id}" && init?.path?.id === plan.id)
      return ok({ ...plan, action: "today", length, started_at: "2026-11-16T09:00:00Z", finished_at, rated });
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
let length: Schemas["NewSession"]["length"] = "25";

// The screen loads the session from GET /api/sessions/{id}, so a fresh render is also a reload.
const start = (options: { length?: Schemas["NewSession"]["length"]; id?: string } = {}) => {
  length = options.length ?? "25";
  return render(
    <MemoryRouter initialEntries={[`/sessions/${options.id ?? SESSION_ID}`]}>
      <Routes>
        <Route path="/" element={<h1>Home</h1>} />
        <Route path="/sessions/:id" element={<Session />} />
      </Routes>
    </MemoryRouter>,
  );
};

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

describe("Pending requests", () => {
  it("posts one rating when the buttons are tapped twice", async () => {
    start();
    await reveal();
    const easy = await button(/^easy$/i);

    fireEvent.click(easy);
    fireEvent.click(easy);

    await screen.findByText("Play B♭ major, 2nd inversion, on G-B-E");
    expect(ratedItems()).toEqual(["shape:minor:1"]);
  });

  it("stays on the card when a rating is rejected, and the retry advances", async () => {
    post.mockImplementationOnce(() => failure(500));
    start();
    await reveal();

    fireEvent.click(await button(/^easy$/i));

    expect((await screen.findByRole("alert")).textContent).toMatch(/couldn't reach the server/i);
    screen.getByText("Play F♯ minor, 1st inversion, on G-B-E");
    await rate();
    await screen.findByText("Play B♭ major, 2nd inversion, on G-B-E");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("says the session is finished when a rating gets a 409", async () => {
    post.mockImplementationOnce(() => failure(409));
    start();
    await reveal();

    fireEvent.click(await button(/^easy$/i));

    expect((await screen.findByRole("alert")).textContent).toMatch(/session is finished/i);
  });
});

describe("Last step", () => {
  beforeEach(() => {
    plan = { id: SESSION_ID, steps: [reviewsThenLesson.steps[0]] };
    mockApi(plan);
  });

  it("leaves only Finish when finishing fails after the last rating, and the retry finishes", async () => {
    const respond = post.getMockImplementation()!;
    post.mockImplementationOnce(respond).mockImplementationOnce(() => failure(500));
    start();
    await reveal();

    fireEvent.click(await button(/^easy$/i));

    await screen.findByRole("alert");
    expect(screen.queryByRole("button", { name: /^easy$/i })).toBeNull();
    fireEvent.click(await button(/^finish$/i));
    await screen.findByRole("heading", { name: /summary/i });
    expect(ratedItems()).toEqual(["shape:minor:1"]);
    expect(callsTo("/api/sessions/{id}/finish")).toHaveLength(2);
  });
});

describe("Wrap up", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("is disabled while a rating is in flight", async () => {
    let saved = (_: unknown) => {};
    const respond = post.getMockImplementation()!;
    post.mockImplementationOnce(() => new Promise((resolve) => (saved = resolve)));
    start();
    await reveal();
    act(() => vi.advanceTimersByTime(25 * 60_000));

    fireEvent.click(await button(/^easy$/i));

    const wrapUp = await button(/wrap up/i);
    expect(wrapUp).toHaveProperty("disabled", true);
    await act(async () => saved(await respond("/api/sessions/{id}/ratings", { path: { id: SESSION_ID } })));
    expect(wrapUp).toHaveProperty("disabled", false);
  });
});

describe("Failed loads", () => {
  it("says the session wasn't found for a non-numeric id, without calling the API", async () => {
    start({ id: "abc" });

    await screen.findByText(/session not found/i);
    expect(get).not.toHaveBeenCalled();
  });

  it.each(["0x10", "1e3"])("says the session wasn't found for id %s, without calling the API", async (id) => {
    start({ id });

    await screen.findByText(/session not found/i);
    expect(get).not.toHaveBeenCalled();
  });

  it("says the session wasn't found when the API returns 404", async () => {
    start({ id: "999" });

    expect((await screen.findByRole("alert")).textContent).toBe("Session not found.");
    expect(get).toHaveBeenCalledWith("/api/sessions/{id}", { path: { id: 999 } });
  });

  it("shows an alert when the session can't be loaded", async () => {
    get.mockImplementation(() => failure(500));
    start();

    await screen.findByRole("alert");
    expect(screen.queryByText(/loading/i)).toBeNull();
  });

  it("shows an alert when a step's content can't be loaded", async () => {
    plan = standalonePassage;
    mockApi(plan);
    const loadSession = get.getMockImplementation()!;
    get.mockImplementation((path, init) => (path === "/api/passages/{id}" ? failure(500) : loadSession(path, init)));
    start();

    await screen.findByRole("alert");
    expect(screen.queryByText(/loading/i)).toBeNull();
  });
});

describe("Resume", () => {
  it("loads the session named by the route", async () => {
    start();

    await screen.findByText("Play F♯ minor, 1st inversion, on G-B-E");
    expect(get).toHaveBeenCalledWith("/api/sessions/{id}", { path: { id: SESSION_ID } });
  });

  it("resumes mid-reviews at the first unrated review", async () => {
    mockApi(plan, { rated: ["shape:minor:1"] });
    start();

    await screen.findByText("Play B♭ major, 2nd inversion, on G-B-E");
  });

  it("resumes mid-lesson at its first unrated shape", async () => {
    mockApi(plan, { rated: FULL_SESSION_ITEMS.slice(0, 3) });
    start();

    await screen.findByText("Rate the 1st inversion");
    await rate();
    expect(ratedItems()).toEqual(["shape:diminished:1"]);
  });

  it("resumes at the next review when a later lesson has the rated item", async () => {
    plan = reviewThenItsLesson;
    mockApi(plan, { rated: ["shape:diminished:0"] });
    start();

    await screen.findByText("Play C major, root position, on G-B-E");
  });

  it("resumes a lesson at its root position when only an earlier review rated that shape", async () => {
    plan = reviewThenItsLesson;
    mockApi(plan, { rated: ["shape:diminished:0", "shape:major:0", "shape:minor:1"] });
    start();

    await screen.findByText("Rate the root position");
    await rate();
    expect(ratedItems()).toEqual(["shape:diminished:0"]);
  });

  it("resumes at the next review when a review's rating was saved twice", async () => {
    mockApi(plan, { rated: ["shape:minor:1", "shape:minor:1"] });
    start();

    await screen.findByText("Play B♭ major, 2nd inversion, on G-B-E");
  });

  it("resumes mid-lesson at its first unrated shape when a shape's rating was saved twice", async () => {
    mockApi(plan, { rated: [...FULL_SESSION_ITEMS.slice(0, 3), "shape:diminished:0"] });
    start();

    await screen.findByText("Rate the 1st inversion");
    await rate();
    expect(ratedItems()).toEqual(["shape:diminished:1"]);
  });

  it("resumes at the lesson's challenge once its passage is rated", async () => {
    mockApi(plan, { rated: FULL_SESSION_ITEMS });
    start();

    await screen.findByText(CARD);
  });

  it("resumes at a passage's challenge once the passage is rated", async () => {
    plan = standalonePassage;
    mockApi(plan, { rated: ["passage:let-it-be"] });
    start();

    await screen.findByText("Same chords, reggae offbeat strum.");
  });

  it("sends the player home when the session is finished", async () => {
    mockApi(plan, { rated: FULL_SESSION_ITEMS, finished_at: "2026-11-16T09:25:00Z" });
    start();

    await screen.findByRole("heading", { name: "Home" });
  });
});
