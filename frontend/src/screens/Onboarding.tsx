import { useEffect, useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api";
import type { components } from "../api-schema";
import Fretboard from "../components/Fretboard";

type Answers = components["schemas"]["Onboarding"];
type Check = components["schemas"]["Check"];
type Quality = Answers["claimed_qualities"][number];

const QUALITIES: Quality[] = ["major", "minor", "diminished", "augmented"];
const STUCK: [Answers["stuck_on"], string][] = [
  ["same_material", "Repeating the same material"],
  ["what_to_practice", "Not knowing what to practice"],
  ["technique", "Technique"],
  ["theory", "Theory"],
];
const GRADES: [Check["playing"], string][] = [
  ["got_it", "Got it"],
  ["close", "Close"],
  ["no_idea", "No idea"],
];
// Asked in A, not the C of the playing prompt, so the answer can't be read off the diagram.
const A_TRIADS: Record<Quality, string> = {
  major: "A C♯ E",
  minor: "A C E",
  diminished: "A C E♭",
  augmented: "A C♯ E♯",
};
const TOP_STRINGS = [3, 2, 1] as const;
// One column, since the phone sits on a music stand (§9).
const STACK = { display: "grid", gap: "0.75rem", justifyItems: "start" } as const;

function QualityCheck({ quality, onDone }: { quality: Quality; onDone: (check: Check) => void }) {
  const [shape, setShape] = useState<number[]>();
  const [revealed, setRevealed] = useState(false);
  const [playing, setPlaying] = useState<Check["playing"]>();

  useEffect(() => {
    api.get("/api/lessons/{quality}", { path: { quality } }).then((r) => r.ok && setShape(r.data.shapes[0]));
  }, [quality]);

  return (
    <section style={STACK}>
      {/* C is the first root in the rotation (§5.1). */}
      <p>{`Play C ${quality}, root position`}</p>
      {!revealed ? (
        <button type="button" onClick={() => setRevealed(true)}>
          Reveal
        </button>
      ) : !playing ? (
        <>
          {shape && (
            <Fretboard
              positions={shape.map((fret, i) => ({ string: TOP_STRINGS[i], fret, root: i === 0 }))}
            />
          )}
          <div>
            {GRADES.map(([grade, label]) => (
              <button key={grade} type="button" onClick={() => setPlaying(grade)}>
                {label}
              </button>
            ))}
          </div>
        </>
      ) : (
        <fieldset style={STACK}>
          <legend>{`Which notes make up A ${quality}?`}</legend>
          {QUALITIES.map((q) => (
            <button key={q} type="button" onClick={() => onDone({ playing, theory_correct: q === quality })}>
              {A_TRIADS[q]}
            </button>
          ))}
        </fieldset>
      )}
    </section>
  );
}

export default function Onboarding() {
  const navigate = useNavigate();
  const [years, setYears] = useState("");
  const [claimed, setClaimed] = useState<Quality[]>([]);
  const [stuck, setStuck] = useState<Answers["stuck_on"]>();
  const [asked, setAsked] = useState(false);
  const [checks, setChecks] = useState<Record<string, Check>>({});
  const [cue, setCue] = useState("");
  const [weeklyGoal, setWeeklyGoal] = useState("4");
  const [failed, setFailed] = useState(false);

  const toCheck = QUALITIES.filter((q) => claimed.includes(q));
  const current = toCheck.find((q) => !(q in checks));

  async function submit() {
    const result = await api.post("/api/onboarding", {
      body: {
        years_playing: Number(years),
        stuck_on: stuck!,
        cue: cue.trim(),
        weekly_goal_days: Number(weeklyGoal),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        claimed_qualities: toCheck,
        checks,
      },
    });
    if (result.ok) navigate("/");
    else setFailed(true);
  }

  if (!asked)
    return (
      <main style={STACK}>
        <label>
          Years playing
          <input type="number" min={0} value={years} onChange={(e) => setYears(e.target.value)} />
        </label>
        <fieldset style={STACK}>
          <legend>Which triads do you already know on the top strings?</legend>
          {QUALITIES.map((q) => (
            <label key={q}>
              <input
                type="checkbox"
                checked={claimed.includes(q)}
                onChange={() => setClaimed(claimed.includes(q) ? claimed.filter((c) => c !== q) : [...claimed, q])}
              />
              {q}
            </label>
          ))}
        </fieldset>
        <fieldset style={STACK}>
          <legend>What feels stuck?</legend>
          {STUCK.map(([value, label]) => (
            <label key={value}>
              <input type="radio" name="stuck" checked={stuck === value} onChange={() => setStuck(value)} />
              {label}
            </label>
          ))}
        </fieldset>
        <button type="button" disabled={!years || !stuck} onClick={() => setAsked(true)}>
          Next
        </button>
      </main>
    );

  if (current)
    return (
      <main style={STACK}>
        <QualityCheck key={current} quality={current} onDone={(check) => setChecks({ ...checks, [current]: check })} />
      </main>
    );

  return (
    <main style={STACK}>
      <label>
        After…, I'll practice.
        <input value={cue} onChange={(e) => setCue(e.target.value)} placeholder="after dinner" />
      </label>
      <label>
        Weekly goal (days)
        <input type="number" min={1} max={7} value={weeklyGoal} onChange={(e) => setWeeklyGoal(e.target.value)} />
      </label>
      <button type="button" disabled={!cue.trim()} onClick={submit}>
        Start practicing
      </button>
      {failed && <p role="alert">Couldn't save. Try again.</p>}
    </main>
  );
}
