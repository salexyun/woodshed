import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ReviewCard from "./ReviewCard";

const PROMPT = "Play F♯ minor, 1st inversion, on G-B-E";

function renderCard(onRate = vi.fn()) {
  render(<ReviewCard prompt={PROMPT} answer={<p>diagram</p>} onRate={onRate} />);
  return onRate;
}

const reveal = () => fireEvent.click(screen.getByRole("button", { name: /reveal/i }));

describe("ReviewCard", () => {
  it("shows the prompt and hides the answer and ratings before reveal", () => {
    renderCard();

    screen.getByText(PROMPT);
    expect(screen.queryByText("diagram")).toBeNull();
    expect(screen.queryByRole("button", { name: /^easy$/i })).toBeNull();
  });

  it("shows the answer and ratings after reveal", () => {
    renderCard();

    reveal();

    screen.getByText("diagram");
    screen.getByRole("button", { name: /^easy$/i });
    expect(screen.queryByRole("button", { name: /reveal/i })).toBeNull();
  });

  it.each(["easy", "challenging", "unfamiliar"])("passes the %s rating to onRate", (rating) => {
    const onRate = renderCard();

    reveal();
    fireEvent.click(screen.getByRole("button", { name: new RegExp(`^${rating}$`, "i") }));

    expect(onRate).toHaveBeenCalledExactlyOnceWith(rating);
  });
});
