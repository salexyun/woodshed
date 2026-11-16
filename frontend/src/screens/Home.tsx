import { useEffect, useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api";
import type { components } from "../api-schema";

type Summary = components["schemas"]["Home"];
type Length = components["schemas"]["NewSession"]["length"];
type Action = components["schemas"]["NewSession"]["action"];

const ACTIONS: [Action, string][] = [
  ["today", "Today's plan"],
  ["continue", "Continue"],
  ["test_me", "Test me"],
];
const LENGTHS: [Length, string][] = [
  ["25", "25 min"],
  ["open", "Open-ended"],
];
// Radios and buttons share one tap-target height, so each is as easy to hit.
const TARGET = "3rem";
const BUTTON = { padding: "0.75rem", fontSize: "1rem", minHeight: TARGET };
const CHOICE = { display: "flex", alignItems: "center", gap: "0.5rem", minHeight: TARGET };
const UNREACHABLE = "Couldn't reach the server. Try again.";

export default function Home() {
  const [home, setHome] = useState<Summary>();
  const [length, setLength] = useState<Length>("25");
  const [error, setError] = useState<string>();
  const [starting, setStarting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/api/home").then((result) => (result.ok ? setHome(result.data) : setError(UNREACHABLE)));
  }, []);

  async function start(action: Action) {
    setStarting(true);
    const result = await api.post("/api/sessions", { body: { action, length } });
    // The session screen reads the plan from router state, so it needn't fetch it again.
    if (result.ok) navigate(`/sessions/${result.data.id}`, { state: { plan: result.data, length } });
    else {
      // Continue is enabled until Home loads, so it can reach a finished course.
      const done = result.error.kind === "http" && result.error.status === 409;
      setError(done ? "All lessons are done, so there's nothing to continue." : UNREACHABLE);
      setStarting(false);
    }
  }

  return (
    <main>
      <h1>Woodshed</h1>
      {error && <p role="alert">{error}</p>}
      {home && (
        <ul>
          <li>{home.streak}-day streak</li>
          <li>
            {home.week_days} of {home.weekly_goal_days} days this week
          </li>
          <li>
            {home.due_count} {home.due_count === 1 ? "review" : "reviews"} due
          </li>
          <li>{home.next_lesson ? `Next lesson: ${home.next_lesson}` : "All lessons done"}</li>
          <li>Cue: {home.cue}</li>
        </ul>
      )}
      <fieldset>
        <legend>Length</legend>
        {LENGTHS.map(([value, label]) => (
          <label key={value} style={CHOICE}>
            <input type="radio" name="length" checked={length === value} onChange={() => setLength(value)} />
            {label}
          </label>
        ))}
      </fieldset>
      {/* One full-width column of large targets: the phone sits on a music stand. */}
      <div style={{ display: "grid", gap: "0.5rem" }}>
        {ACTIONS.map(([action, label]) => (
          <button
            key={action}
            type="button"
            style={BUTTON}
            // A finished course has no lesson to continue; Continue would post an empty session.
            disabled={starting || (action === "continue" && home?.next_lesson === null)}
            onClick={() => start(action)}
          >
            {label}
          </button>
        ))}
        <button type="button" style={BUTTON} onClick={() => navigate(`/pick-a-song?length=${length}`)}>
          Pick a song
        </button>
      </div>
    </main>
  );
}
