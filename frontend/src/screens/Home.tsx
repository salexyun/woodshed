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
const BUTTON = { padding: "0.75rem", fontSize: "1rem" };

export default function Home() {
  const [home, setHome] = useState<Summary>();
  const [length, setLength] = useState<Length>("25");
  const [failed, setFailed] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/api/home").then((result) => (result.ok ? setHome(result.data) : setFailed(true)));
  }, []);

  async function start(action: Action) {
    const result = await api.post("/api/sessions", { body: { action, length } });
    // The session screen reads the plan from router state, so it needn't fetch it again.
    if (result.ok) navigate(`/sessions/${result.data.id}`, { state: { plan: result.data, length } });
    else setFailed(true);
  }

  return (
    <main>
      <h1>Woodshed</h1>
      {failed && <p role="alert">Couldn't reach the server. Try again.</p>}
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
          <label key={value}>
            <input type="radio" name="length" checked={length === value} onChange={() => setLength(value)} />
            {label}
          </label>
        ))}
      </fieldset>
      {/* One full-width column of large targets: the phone sits on a music stand. */}
      <div style={{ display: "grid", gap: "0.5rem" }}>
        {ACTIONS.map(([action, label]) => (
          <button key={action} type="button" style={BUTTON} onClick={() => start(action)}>
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
