import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { api } from "../api";
import type { components } from "../api-schema";

type Passage = components["schemas"]["Passage"];
type Length = components["schemas"]["NewSession"]["length"];

const BUTTON = { padding: "0.75rem", fontSize: "1rem" };

export default function PickASong() {
  const [passages, setPassages] = useState<Passage[]>();
  const [failed, setFailed] = useState(false);
  const [starting, setStarting] = useState(false);
  const length: Length = useSearchParams()[0].get("length") === "open" ? "open" : "25";
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/api/passages").then((result) => (result.ok ? setPassages(result.data) : setFailed(true)));
  }, []);

  const unlocked = passages?.filter((p) => p.unlocked);

  async function start(passage: string) {
    setStarting(true);
    const result = await api.post("/api/sessions", { body: { action: "pick_a_song", length, passage } });
    // The session screen reads the plan from router state, so it needn't fetch it again.
    if (result.ok) navigate(`/sessions/${result.data.id}`, { state: { plan: result.data, length } });
    else {
      setFailed(true);
      setStarting(false);
    }
  }

  return (
    <main>
      <h1>Pick a song</h1>
      {failed && <p role="alert">Couldn't reach the server. Try again.</p>}
      {unlocked?.length === 0 && <p>Finish a lesson to unlock songs.</p>}
      <div style={{ display: "grid", gap: "0.5rem" }}>
        {unlocked?.map((p) => (
          <button key={p.id} type="button" style={BUTTON} disabled={starting} onClick={() => start(p.id)}>
            {p.title}
            {p.artist && ` · ${p.artist}`}
          </button>
        ))}
      </div>
    </main>
  );
}
