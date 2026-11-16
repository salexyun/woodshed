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

const num = (el: Element, attr: string) => Number(el.getAttribute(attr));

// Geometry read from the drawn board, not recomputed from layout constants:
// string lines left to right are 6..1, fret wires top to bottom are rows 0..5.
const stringX = (string: number) => {
  const xs = screen.getAllByTestId("string").map((l) => num(l, "x1"));
  return xs.sort((a, b) => a - b)[6 - string];
};
const wireYs = (container: HTMLElement) =>
  [...container.querySelectorAll("line:not([data-testid])")]
    .filter((l) => num(l, "y1") === num(l, "y2"))
    .map((l) => num(l, "y1"))
    .sort((a, b) => a - b);

const dotAt = (string: number) => {
  const dot = screen
    .getAllByTestId("dot")
    .find((d) => d.dataset.string === String(string))!;
  const [, x, y] = dot
    .getAttribute("transform")!
    .match(/translate\(([-\d.]+)[ ,]+([-\d.]+)\)/)!;
  return { x: Number(x), y: Number(y) };
};

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
    expect(
      dots()
        .filter((d) => d.root)
        .map((d) => d.string),
    ).toEqual([rootString]);
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

  it.each([
    ["C root position", cRoot],
    ["open C shape", cOpen],
  ])("marks low E, A and D as muted for %s", (_, positions) => {
    render(<Fretboard positions={positions} />);
    const muted = screen.getAllByTestId("muted");
    expect(muted.map((m) => Number(m.dataset.string)).sort()).toEqual([
      4, 5, 6,
    ]);
    expect(muted.every((m) => m.textContent === "x")).toBe(true);
  });

  it.each([
    ["C root position", cRoot],
    ["open C shape", cOpen],
  ])(
    "draws each muted x on its string above the board for %s",
    (_, positions) => {
      const { container } = render(<Fretboard positions={positions} />);
      const top = wireYs(container)[0];
      for (const m of screen.getAllByTestId("muted")) {
        expect(num(m, "x")).toBe(stringX(Number(m.dataset.string)));
        expect(num(m, "y")).toBeLessThan(top);
      }
    },
  );

  it.each([
    // string, fret, row: a fretted dot sits midway between wires row and row+1
    [3, 5, 2],
    [2, 5, 2],
    [1, 3, 0],
  ])("places C root dot on string %i fret %i in row %i", (string, _, row) => {
    const { container } = render(<Fretboard positions={cRoot} />);
    const wires = wireYs(container);
    expect(dotAt(string)).toEqual({
      x: stringX(string),
      y: (wires[row] + wires[row + 1]) / 2,
    });
  });

  it("places open-string dots on the nut", () => {
    const { container } = render(<Fretboard positions={cOpen} />);
    const nut = wireYs(container)[0];
    expect(dotAt(3)).toEqual({ x: stringX(3), y: nut });
    expect(dotAt(1)).toEqual({ x: stringX(1), y: nut });
  });

  it("renders an empty board for no positions", () => {
    const { container } = render(<Fretboard positions={[]} />);
    expect(screen.queryAllByTestId("dot")).toHaveLength(0);
    expect(screen.getAllByTestId("string")).toHaveLength(6);
    expect(container.innerHTML).not.toMatch(/Infinity|NaN/);
  });
});
