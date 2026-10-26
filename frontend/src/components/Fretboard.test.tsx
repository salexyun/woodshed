import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Fretboard, { type Position } from "./Fretboard";

// C major on G-B-E (§4): root position 5-5-3, 2nd inversion 0-1-0.
const cRoot: Position[] = [
  { string: "G", fret: 5, root: true },
  { string: "B", fret: 5 },
  { string: "E", fret: 3 },
];
const cOpen: Position[] = [
  { string: "G", fret: 0 },
  { string: "B", fret: 1, root: true },
  { string: "E", fret: 0 },
];

const dots = () =>
  screen.getAllByTestId("dot").map((dot) => ({
    string: dot.dataset.string,
    fret: Number(dot.dataset.fret),
    root: dot.dataset.root === "true",
  }));

describe("Fretboard", () => {
  it("renders an svg with 3 strings", () => {
    const { container } = render(<Fretboard positions={cRoot} />);
    expect(container.querySelector("svg")).not.toBeNull();
    expect(screen.getAllByTestId("string")).toHaveLength(3);
  });

  it.each([
    ["C root position", cRoot],
    ["open C shape", cOpen],
  ])("renders one dot per position for %s", (_, positions) => {
    render(<Fretboard positions={positions} />);
    const expected = positions.map((p) => ({ ...p, root: p.root ?? false }));
    expect(dots()).toHaveLength(expected.length);
    expect(dots()).toEqual(expect.arrayContaining(expected));
  });

  it.each([
    ["C root position", cRoot, "G"],
    ["open C shape", cOpen, "B"],
  ])("marks only the root for %s", (_, positions, rootString) => {
    render(<Fretboard positions={positions} />);
    expect(dots().filter((d) => d.root).map((d) => d.string)).toEqual([
      rootString,
    ]);
  });

  it("draws the nut when the window starts at fret 0", () => {
    render(<Fretboard positions={cOpen} />);
    expect(screen.queryByTestId("nut")).not.toBeNull();
  });

  it("labels the lowest fret and omits the nut up the neck", () => {
    render(<Fretboard positions={cRoot} />);
    expect(screen.queryByTestId("nut")).toBeNull();
    expect(screen.getByTestId("start-fret").textContent).toBe("3");
  });
});
