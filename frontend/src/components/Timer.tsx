import { useEffect, useState } from "react";

const COUNTDOWN_SECONDS = 25 * 60;
const STOP_HINT_SECONDS = 60 * 60;
// Several ticks a second, so a late tick never skips a displayed second.
const TICK_MS = 250;

type Props = { mode: "countdown" | "countup"; onWrapUp: () => void; busy?: boolean };

const pad = (n: number) => String(n).padStart(2, "0");
export const format = (seconds: number) => `${pad(Math.floor(seconds / 60))}:${pad(seconds % 60)}`;

export default function Timer({ mode, onWrapUp, busy = false }: Props) {
  const [start] = useState(Date.now);
  const [now, setNow] = useState(start);
  const [keptGoing, setKeptGoing] = useState(false);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(id);
  }, []);

  // Measured against the start time rather than counted in ticks, so the display can't drift.
  const elapsed = Math.floor((now - start) / 1000);
  const countingUp = mode === "countup" || keptGoing;
  const timeUp = !countingUp && elapsed >= COUNTDOWN_SECONDS;

  return (
    <div>
      <p role="timer">{format(countingUp ? elapsed : Math.max(COUNTDOWN_SECONDS - elapsed, 0))}</p>
      {timeUp && (
        <>
          <button type="button" onClick={onWrapUp} disabled={busy}>
            Wrap up
          </button>
          <button type="button" onClick={() => setKeptGoing(true)}>
            Keep going
          </button>
        </>
      )}
      {countingUp && elapsed >= STOP_HINT_SECONDS && <p>Diminishing returns; let it consolidate.</p>}
    </div>
  );
}
