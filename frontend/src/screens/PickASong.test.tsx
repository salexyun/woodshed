import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import type { components } from "../api-schema";
import PickASong from "./PickASong";

vi.mock("../api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));

type Passage = components["schemas"]["Passage"];

const passage = (id: string, title: string, unlocked: boolean): Passage => ({
  id,
  title,
  artist: null,
  kind: "song",
  chords: ["C", "F", "G"],
  lesson: "major",
  unlocked,
});

const PASSAGES = [
  passage("la-bamba", "La Bamba", true),
  passage("twist-and-shout", "Twist and Shout", true),
  passage("let-it-be", "Let It Be", false),
];

function CurrentPath() {
  return <p>at {useLocation().pathname}</p>;
}

function renderScreen(length = "25") {
  vi.mocked(api.get).mockResolvedValue({ ok: true, data: PASSAGES });
  vi.mocked(api.post).mockResolvedValue({ ok: true, data: { id: 7, steps: [] } });
  render(
    <MemoryRouter initialEntries={[`/pick-a-song?length=${length}`]}>
      <Routes>
        <Route path="/pick-a-song" element={<PickASong />} />
        <Route path="/sessions/:id" element={<CurrentPath />} />
      </Routes>
    </MemoryRouter>,
  );
}

const start = async (title: RegExp) =>
  fireEvent.click(await screen.findByRole("button", { name: title }));

afterEach(() => vi.resetAllMocks());

describe("PickASong", () => {
  it("lists only the unlocked passages", async () => {
    renderScreen();

    await screen.findByRole("button", { name: /la bamba/i });
    screen.getByRole("button", { name: /twist and shout/i });
    expect(screen.queryByText(/let it be/i)).toBeNull();
    expect(api.get).toHaveBeenCalledWith("/api/passages");
  });

  it.each(["25", "open"])("starts a pick_a_song session at the URL's length %s", async (length) => {
    renderScreen(length);

    await start(/twist and shout/i);

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/sessions", {
        body: { action: "pick_a_song", length, passage: "twist-and-shout" },
      }),
    );
  });

  it("opens the started session", async () => {
    renderScreen();

    await start(/la bamba/i);

    await screen.findByText("at /sessions/7");
  });
});
