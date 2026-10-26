import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Timer from "./Timer";

const MINUTE = 60_000;
const STOP_HINT = /diminishing returns; let it consolidate/i;

const advance = (ms: number) => act(() => vi.advanceTimersByTime(ms));
const wrapUp = () => screen.queryByRole("button", { name: /wrap up/i });
const keepGoing = () => screen.queryByRole("button", { name: /keep going/i });

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("Timer countdown", () => {
  it("counts down from 25:00", () => {
    render(<Timer mode="countdown" onWrapUp={vi.fn()} />);
    screen.getByText("25:00");

    advance(1000);

    screen.getByText("24:59");
  });

  it("has no prompt before 0", () => {
    render(<Timer mode="countdown" onWrapUp={vi.fn()} />);

    advance(25 * MINUTE - 1000);

    expect(wrapUp()).toBeNull();
    expect(keepGoing()).toBeNull();
  });

  it("offers wrap up or keep going at 0 without ending the session", () => {
    const onWrapUp = vi.fn();
    render(<Timer mode="countdown" onWrapUp={onWrapUp} />);

    advance(25 * MINUTE);

    expect(wrapUp()).not.toBeNull();
    expect(keepGoing()).not.toBeNull();
    expect(onWrapUp).not.toHaveBeenCalled();
  });

  it("calls onWrapUp when the player wraps up", () => {
    const onWrapUp = vi.fn();
    render(<Timer mode="countdown" onWrapUp={onWrapUp} />);
    advance(25 * MINUTE);

    fireEvent.click(wrapUp()!);

    expect(onWrapUp).toHaveBeenCalledOnce();
  });

  it("switches to counting up when the player keeps going", () => {
    render(<Timer mode="countdown" onWrapUp={vi.fn()} />);
    advance(25 * MINUTE);

    fireEvent.click(keepGoing()!);
    const before = screen.getByRole("timer").textContent;
    advance(1000);

    expect(wrapUp()).toBeNull();
    expect(keepGoing()).toBeNull();
    expect(screen.getByRole("timer").textContent).not.toBe(before);
  });

  it("keeps counting total session time after keep going, so the hint comes at 60 minutes total", () => {
    render(<Timer mode="countdown" onWrapUp={vi.fn()} />);
    advance(25 * MINUTE);
    fireEvent.click(keepGoing()!);
    screen.getByText("25:00");

    advance(35 * MINUTE - 1000);
    expect(screen.queryByText(STOP_HINT)).toBeNull();

    advance(1000);
    screen.getByText("60:00");
    screen.getByText(STOP_HINT);
  });
});

describe("Timer count-up", () => {
  it("counts up from 00:00", () => {
    render(<Timer mode="countup" onWrapUp={vi.fn()} />);
    screen.getByText("00:00");

    advance(1000);

    screen.getByText("00:01");
  });

  it("has no stop suggestion before 60 minutes", () => {
    render(<Timer mode="countup" onWrapUp={vi.fn()} />);

    advance(60 * MINUTE - 1000);

    expect(screen.queryByText(STOP_HINT)).toBeNull();
  });

  it("suggests stopping at 60 minutes without ending the session", () => {
    const onWrapUp = vi.fn();
    render(<Timer mode="countup" onWrapUp={onWrapUp} />);

    advance(60 * MINUTE);

    screen.getByText(STOP_HINT);
    screen.getByText("60:00");
    expect(onWrapUp).not.toHaveBeenCalled();
  });
});
