import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Fretboard, { type Position } from "./Fretboard";

// C major on G-B-E = strings 3-2-1 (§4): root position 5-5-3, 2nd inversion 0-1-0.
const cRoot: Position[] = [
  { string: 3, fret: 5, root: true },
  { string: 2, fret: 5 },
  { string: 1, fret: 3 },
];
const cOpen: Position[] = [
  { string: 3, fret: 0 },
  { string: 2, fret: 1, root: true },
  { string: 1, fret: 0 },
];

const dots = () =>
  screen.getAllByTestId("dot").map((dot) => ({
    string: Number(dot.dataset.string),
    fret: Number(dot.dataset.fret),
    root: dot.dataset.root === "true",
  }));

describe("Fretboard", () => {
  it("renders an svg with 6 strings", () => {
    const { container } = render(<Fretboard positions={cRoot} />);
    expect(container.querySelector("svg")).not.toBeNull();
    expect(screen.getAllByTestId("string")).toHaveLength(6);
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
    ["C root position", cRoot, 3],
    ["open C shape", cOpen, 2],
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
