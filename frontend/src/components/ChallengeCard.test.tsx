import { render, screen } from "@testing-library/react";
import { describe, it } from "vitest";

import ChallengeCard from "./ChallengeCard";

describe("ChallengeCard", () => {
  it("shows the challenge text", () => {
    render(<ChallengeCard text="Play it up an octave." />);

    screen.getByText("Play it up an octave.");
  });
});
