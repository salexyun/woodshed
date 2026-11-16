import { useEffect, useState, type FormEvent } from "react";

import { api } from "../api";
import type { components } from "../api-schema";

type Schemas = components["schemas"];
type Quality = Schemas["Lesson"]["quality"];

const QUALITIES: Quality[] = ["major", "minor", "diminished", "augmented"];
const INVERSIONS = ["root position", "1st inversion", "2nd inversion"];
const ACTIONS: Record<Schemas["PastSession"]["action"], string> = {
  today: "Today's plan",
  continue: "Continue",
  test_me: "Test me",
  pick_a_song: "Pick a song",
};
// Box 1 (just learned) to box 5 (well known), light to dark green.
const BOX_COLORS = ["#d9f0d3", "#a6dba0", "#5aae61", "#1b7837", "#00441b"];

const minutes = (seconds: number | null) =>
  seconds === null ? "—" : seconds < 60 ? "<1 min" : `${Math.round(seconds / 60)} min`;

export default function Progress() {
  const [boxes, setBoxes] = useState<Map<string, number>>();
  const [sessions, setSessions] = useState<Schemas["PastSession"][]>();
  const [date, setDate] = useState<Intl.DateTimeFormat>();
  const [cue, setCue] = useState("");
  const [goal, setGoal] = useState("");
  const [failed, setFailed] = useState(false);
  const [rejected, setRejected] = useState(false);

  useEffect(() => {
    api.get("/api/progress").then((r) => (r.ok ? setBoxes(new Map(r.data.map((i) => [i.id, i.box]))) : setFailed(true)));
    api.get("/api/sessions").then((r) => (r.ok ? setSessions(r.data) : setFailed(true)));
    api.get("/api/profile").then((r) => {
      if (!r.ok) return setFailed(true);
      // en-CA formats dates as YYYY-MM-DD; practice days are local to the profile's timezone.
      setDate(new Intl.DateTimeFormat("en-CA", { timeZone: r.data.timezone }));
      setCue(r.data.cue);
      setGoal(String(r.data.weekly_goal_days));
    });
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    const result = await api.patch("/api/profile", { body: { cue, weekly_goal_days: Number(goal) } });
    setRejected(false);
    if (result.ok) return;
    if (result.error.kind === "http" && result.error.status === 422) setRejected(true);
    else setFailed(true);
  }

  return (
    <main>
      <h1>Progress</h1>
      {failed && <p role="alert">Couldn't reach the server. Try again.</p>}
      {boxes && (
        <div style={{ display: "grid", gridTemplateColumns: "auto repeat(3, 1fr)", gap: "0.25rem" }}>
          <span />
          {INVERSIONS.map((inversion) => (
            <small key={inversion}>{inversion}</small>
          ))}
          {QUALITIES.map((quality) => [
            <span key={quality}>{quality}</span>,
            ...INVERSIONS.map((inversion, i) => {
              const box = boxes.get(`shape:${quality}:${i}`);
              return (
                <span
                  key={`${quality}:${i}`}
                  role="img"
                  aria-label={`${quality}, ${inversion}`}
                  data-box={box}
                  title={box ? `box ${box}` : "not started"}
                  style={{ minHeight: "2rem", border: "1px solid #ccc", background: box ? BOX_COLORS[box - 1] : "none" }}
                />
              );
            }),
          ])}
        </div>
      )}
      {sessions && date && (
        <table style={{ width: "100%" }}>
          <caption>History</caption>
          <thead>
            <tr>
              <th>Date</th>
              <th>Length</th>
              <th>Action</th>
              <th>Items</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td>{date.format(new Date(s.started_at))}</td>
                <td>{minutes(s.duration_seconds)}</td>
                <td>{ACTIONS[s.action]}</td>
                <td>
                  {s.items_rated} {s.items_rated === 1 ? "item" : "items"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {/* The profile also sets the date format, so the form waits for it instead of saving blanks. */}
      {date && (
        <form onSubmit={save} style={{ display: "grid", gap: "0.5rem" }}>
          <label>
            Cue <input value={cue} onChange={(e) => setCue(e.target.value)} />
          </label>
          <label>
            Weekly goal (days){" "}
            <input type="number" min={1} max={7} value={goal} onChange={(e) => setGoal(e.target.value)} />
          </label>
          {rejected && <p role="alert">Couldn't save. The cue can't be empty and the goal is 1 to 7 days.</p>}
          <button type="submit" style={{ padding: "0.75rem", fontSize: "1rem" }}>
            Save
          </button>
        </form>
      )}
    </main>
  );
}
