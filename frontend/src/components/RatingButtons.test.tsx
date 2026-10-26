import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import RatingButtons from "./RatingButtons";

describe("RatingButtons", () => {
  it.each(["easy", "challenging", "unfamiliar"])("calls onRate with %s", (rating) => {
    const onRate = vi.fn();
    render(<RatingButtons onRate={onRate} />);

    fireEvent.click(screen.getByRole("button", { name: new RegExp(`^${rating}$`, "i") }));

    expect(onRate).toHaveBeenCalledExactlyOnceWith(rating);
  });
});
