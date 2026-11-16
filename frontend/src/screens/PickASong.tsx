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
  const length: Length = useSearchParams()[0].get("length") === "open" ? "open" : "25";
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/api/passages").then((result) => (result.ok ? setPassages(result.data) : setFailed(true)));
  }, []);

  async function start(passage: string) {
    const result = await api.post("/api/sessions", { body: { action: "pick_a_song", length, passage } });
    // The session screen reads the plan from router state, so it needn't fetch it again.
    if (result.ok) navigate(`/sessions/${result.data.id}`, { state: { plan: result.data, length } });
    else setFailed(true);
  }

  return (
    <main>
      <h1>Pick a song</h1>
      {failed && <p role="alert">Couldn't reach the server. Try again.</p>}
      <div style={{ display: "grid", gap: "0.5rem" }}>
        {passages
          ?.filter((p) => p.unlocked)
          .map((p) => (
            <button key={p.id} type="button" style={BUTTON} onClick={() => start(p.id)}>
              {p.title}
              {p.artist && ` · ${p.artist}`}
            </button>
          ))}
      </div>
    </main>
  );
}
