import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import type { components } from "../api-schema";
import Onboarding from "./Onboarding";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }));
vi.mock("../api", () => ({ api }));

const PROFILE = {
  years_playing: 3,
  stuck_on: "same_material",
  cue: "after dinner",
  weekly_goal_days: 4,
  timezone: "Asia/Seoul",
};
const HOME: components["schemas"]["Home"] = {
  streak: 0,
  week_days: 0,
  weekly_goal_days: 4,
  due_count: 0,
  next_lesson: "major",
  cue: "after dinner",
};
const NOT_FOUND = { ok: false, error: { kind: "http", status: 404, detail: "not onboarded" } };
// Root-position C shapes on G-B-E, the first root in the rotation (§5.1).
const C_SHAPES = {
  major: [5, 5, 3],
  minor: [5, 4, 3],
  diminished: [5, 4, 2],
  augmented: [5, 5, 4],
} as const;
const A_NOTES = {
  major: "A C♯ E",
  minor: "A C E",
  diminished: "A C E♭",
  augmented: "A C♯ E♯",
} as const;
type Quality = keyof typeof A_NOTES;

let onboarded = false;

beforeEach(() => {
  onboarded = false;
  vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({
    ...new Intl.DateTimeFormat("en-US", { timeZone: "UTC" }).resolvedOptions(),
    timeZone: "Asia/Seoul",
  });
  api.get.mockImplementation(async (path: string, init?: { path?: { quality: Quality } }) => {
    if (path === "/api/profile") return onboarded ? { ok: true, data: PROFILE } : NOT_FOUND;
    if (path === "/api/home") return { ok: true, data: HOME };
    if (path === "/api/lessons/{quality}") {
      const quality = init!.path!.quality;
      const shapes = [C_SHAPES[quality], [0, 0, 0], [0, 0, 0]];
      return { ok: true, data: { quality, explanation: "", shapes, passages: [] } };
    }
    return NOT_FOUND;
  });
  api.post.mockImplementation(async () => {
    onboarded = true;
    return { ok: true, data: PROFILE };
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  api.get.mockReset();
  api.post.mockReset();
});

function renderOnboarding() {
  render(
    <MemoryRouter initialEntries={["/onboarding"]}>
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/" element={<p>home</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

const click = (role: string, name: string | RegExp) =>
  fireEvent.click(screen.getByRole(role, { name }));

async function answerQuestions(qualities: Quality[] = [], stuck = "Repeating the same material") {
  fireEvent.change(await screen.findByLabelText(/years playing/i), { target: { value: "3" } });
  qualities.forEach((q) => click("checkbox", new RegExp(`^${q}$`, "i")));
  click("radio", stuck);
  click("button", /next/i);
}

async function check(quality: Quality, playing = "Got it", theoryCorrect = true) {
  await screen.findByText(new RegExp(`play C ${quality}, root position`, "i"));
  click("button", /reveal/i);
  fireEvent.click(await screen.findByRole("button", { name: playing }));
  const question = await screen.findByRole("group", {
    name: new RegExp(`which notes make up A ${quality}\\?`, "i"),
  });
  const options = within(question).getAllByRole("button");
  const correct = options.find((o) => o.textContent === A_NOTES[quality])!;
  fireEvent.click(theoryCorrect ? correct : options.find((o) => o !== correct)!);
}

async function setUpHabit(cue = "after dinner") {
  fireEvent.change(await screen.findByLabelText(/^after/i), { target: { value: cue } });
}

const submit = () => click("button", /start practicing/i);
const submitted = () => api.post.mock.lastCall!;

describe("Onboarding questions", () => {
  it("asks years playing, known qualities and what feels stuck", async () => {
    renderOnboarding();

    await screen.findByLabelText(/years playing/i);
    for (const q of Object.keys(A_NOTES)) screen.getByRole("checkbox", { name: new RegExp(`^${q}$`, "i") });
    for (const stuck of [
      "Repeating the same material",
      "Not knowing what to practice",
      "Technique",
      "Theory",
    ])
      screen.getByRole("radio", { name: stuck });
  });

  it.each([
    ["Repeating the same material", "same_material"],
    ["Not knowing what to practice", "what_to_practice"],
    ["Technique", "technique"],
    ["Theory", "theory"],
  ])("submits %s as stuck_on %s", async (label, value) => {
    renderOnboarding();
    await answerQuestions([], label);
    await setUpHabit();
    submit();

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(submitted()[1].body.stuck_on).toBe(value);
  });
});

describe("Onboarding input validation", () => {
  const disabled = (name: RegExp) => (screen.getByRole("button", { name }) as HTMLButtonElement).disabled;

  it.each([
    ["", true],
    ["-1", true],
    ["1.5", true],
    ["0", false],
    ["12", false],
  ])("years playing %j disables Next: %s", async (years, expected) => {
    renderOnboarding();
    fireEvent.change(await screen.findByLabelText(/years playing/i), { target: { value: years } });
    click("radio", "Theory");

    expect(disabled(/next/i)).toBe(expected);
  });

  it.each([
    ["", true],
    ["0", true],
    ["8", true],
    ["2.5", true],
    ["1", false],
    ["7", false],
  ])("weekly goal %j disables Start practicing: %s", async (goal, expected) => {
    renderOnboarding();
    await answerQuestions();
    await setUpHabit();
    fireEvent.change(screen.getByLabelText(/weekly goal/i), { target: { value: goal } });

    expect(disabled(/start practicing/i)).toBe(expected);
  });
});

describe("Onboarding checks", () => {
  it("prompts root-position C and hides the diagram until reveal", async () => {
    renderOnboarding();
    await answerQuestions(["minor"]);

    await screen.findByText(/play C minor, root position/i);
    expect(screen.queryByRole("img", { name: /fretboard/i })).toBeNull();
    click("button", /reveal/i);

    await screen.findByRole("img", { name: /fretboard/i });
    for (const grade of ["Got it", "Close", "No idea"]) screen.getByRole("button", { name: grade });
  });

  it("checks only the claimed qualities, in lesson order", async () => {
    renderOnboarding();
    await answerQuestions(["augmented", "major"]);

    await check("major");
    await check("augmented");
    await setUpHabit();
    submit();

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(Object.keys(submitted()[1].body.checks)).toEqual(["major", "augmented"]);
  });

  it("goes straight to habit setup when no quality is claimed", async () => {
    renderOnboarding();
    await answerQuestions([]);

    await screen.findByLabelText(/^after/i);
    expect(screen.queryByRole("button", { name: /reveal/i })).toBeNull();
  });

  it.each(Object.keys(A_NOTES) as Quality[])(
    "marks the correct notes of A %s as theory_correct",
    async (quality) => {
      renderOnboarding();
      await answerQuestions([quality]);
      await check(quality);
      await setUpHabit();
      submit();

      await waitFor(() => expect(api.post).toHaveBeenCalled());
      expect(submitted()[1].body.checks[quality].theory_correct).toBe(true);
    },
  );

  it.each([
    ["Got it", "got_it"],
    ["Close", "close"],
    ["No idea", "no_idea"],
  ])("records %s as playing %s and a wrong answer as incorrect", async (grade, playing) => {
    renderOnboarding();
    await answerQuestions(["major"]);
    await check("major", grade, false);
    await setUpHabit();
    submit();

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(submitted()[1].body.checks).toEqual({ major: { playing, theory_correct: false } });
  });
});

describe("Onboarding habit setup and submit", () => {
  it("posts the answers, checks and habit to /api/onboarding", async () => {
    renderOnboarding();
    await answerQuestions(["major", "minor"]);
    await check("major");
    await check("minor", "Close");
    await setUpHabit("after dinner");
    fireEvent.change(screen.getByLabelText(/weekly goal/i), { target: { value: "5" } });
    submit();

    await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
    expect(submitted()).toEqual([
      "/api/onboarding",
      {
        body: {
          years_playing: 3,
          stuck_on: "same_material",
          cue: "after dinner",
          weekly_goal_days: 5,
          timezone: "Asia/Seoul",
          claimed_qualities: ["major", "minor"],
          checks: {
            major: { playing: "got_it", theory_correct: true },
            minor: { playing: "close", theory_correct: true },
          },
        },
      },
    ]);
  });

  it("defaults the weekly goal to 4 days", async () => {
    renderOnboarding();
    await answerQuestions();
    await setUpHabit();

    expect((screen.getByLabelText(/weekly goal/i) as HTMLInputElement).value).toBe("4");
    submit();
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(submitted()[1].body.weekly_goal_days).toBe(4);
  });

  it("takes the timezone from the browser", async () => {
    renderOnboarding();
    await answerQuestions();
    await setUpHabit();
    submit();

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(submitted()[1].body.timezone).toBe("Asia/Seoul");
  });

  it("can't submit without a cue", async () => {
    renderOnboarding();
    await answerQuestions();
    await screen.findByLabelText(/^after/i);

    expect((screen.getByRole("button", { name: /start practicing/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("goes home after submitting", async () => {
    renderOnboarding();
    await answerQuestions();
    await setUpHabit();
    submit();

    await screen.findByText("home");
  });
});

describe("App before onboarding", () => {
  const renderApp = (path: string) =>
    render(
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>,
    );

  it.each(["/", "/sessions/1", "/pick-a-song", "/progress"])("redirects %s to onboarding", async (path) => {
    renderApp(path);

    await screen.findByLabelText(/years playing/i);
  });

  it("shows the route once onboarded", async () => {
    onboarded = true;
    renderApp("/");

    await screen.findByRole("button", { name: "Today's plan" });
    await screen.findByText(/next lesson: major/i);
    expect(screen.queryByLabelText(/years playing/i)).toBeNull();
  });

  it.each([
    ["a 500", { kind: "http", status: 500 }],
    ["a network error", { kind: "network" }],
  ])("shows an error instead of redirecting on %s", async (_, error) => {
    api.get.mockResolvedValue({ ok: false, error });
    renderApp("/");

    await screen.findByRole("alert");
    expect(screen.queryByLabelText(/years playing/i)).toBeNull();
  });

  it("stops redirecting after onboarding is submitted", async () => {
    renderApp("/");
    await answerQuestions();
    await setUpHabit();
    submit();

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    await screen.findByRole("button", { name: "Today's plan" });
    await screen.findByText(/next lesson: major/i);
    expect(screen.queryByLabelText(/years playing/i)).toBeNull();
    expect(screen.queryByLabelText(/^after/i)).toBeNull();
  });
});
