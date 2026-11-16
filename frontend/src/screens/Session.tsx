import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";

import { api, type ApiResult } from "../api";
import type { components } from "../api-schema";
import ChallengeCard from "../components/ChallengeCard";
import Fretboard, { type Position } from "../components/Fretboard";
import RatingButtons, { type Rating } from "../components/RatingButtons";
import ReviewCard from "../components/ReviewCard";
import Timer, { format } from "../components/Timer";

type Schemas = components["schemas"];
type Quality = Schemas["Lesson"]["quality"];
type Started = { plan: Schemas["Plan"]; length: Schemas["NewSession"]["length"] };
// Builds the rating handler for one item; `then` runs once the rating is saved.
type Rate = (itemId: string, then: () => void) => (rating: Rating) => void;
type StepProps = { rate: Rate; onDone: () => void; last: boolean };

const INVERSIONS = ["root position", "1st inversion", "2nd inversion"];
// Shapes are given low to high on strings 3-2-1; each inversion puts the root on a different string.
const ROOT_STRING = [3, 1, 2];
const SEMITONES: Record<string, number> = {
  C: 0, "C♯": 1, "D♭": 1, D: 2, "E♭": 3, E: 4, F: 5,
  "F♯": 6, "G♭": 6, G: 7, "A♭": 8, A: 9, "B♭": 10, B: 11,
};

// Home passes the started session in router state; #57 will let a reload fetch it instead.
const useStarted = (): Started | undefined => useLocation().state ?? undefined;

// Each step is keyed, so it remounts and loads once.
function useLoad<T>(load: () => Promise<ApiResult<T>>): T | undefined {
  const [data, setData] = useState<T>();
  useEffect(() => {
    load().then((result) => result.ok && setData(result.data));
  }, []);
  return data;
}

const useLesson = (quality: Quality) =>
  useLoad(() => api.get("/api/lessons/{quality}", { path: { quality } }));
const usePassage = (itemId: string) =>
  useLoad(() => api.get("/api/passages/{id}", { path: { id: itemId.replace(/^passage:/, "") } }));

const positions = (frets: number[], inversion: number): Position[] =>
  frets.map((fret, i) => {
    const string = (3 - i) as Position["string"];
    return { string, fret, root: string === ROOT_STRING[inversion] };
  });

// Lesson shapes are in C; movable shapes reach any root by sliding up, kept below the 12th fret.
function transpose(frets: number[], root: string) {
  const moved = frets.map((fret) => fret + SEMITONES[root]);
  return Math.min(...moved) >= 12 ? moved.map((fret) => fret - 12) : moved;
}

function ShapeReview({ id, root, onRate }: { id: string; root: string; onRate: (r: Rating) => void }) {
  const [, quality, inversion] = id.split(":") as [string, Quality, string];
  const shape = useLesson(quality)?.shapes[Number(inversion)];
  return (
    <ReviewCard
      prompt={`Play ${root} ${quality}, ${INVERSIONS[Number(inversion)]}, on G-B-E`}
      answer={shape && <Fretboard positions={positions(transpose(shape, root), Number(inversion))} />}
      onRate={onRate}
    />
  );
}

function PassageReview({ id, onRate }: { id: string; onRate: (r: Rating) => void }) {
  const passage = usePassage(id);
  if (!passage) return <p>Loading…</p>;
  return (
    <ReviewCard prompt={`Play ${passage.title}`} answer={<p>{passage.chords.join(" ")}</p>} onRate={onRate} />
  );
}

function PassageStep({ id, rate, onDone }: { id: string } & Omit<StepProps, "last">) {
  const passage = usePassage(id);
  if (!passage) return <p>Loading…</p>;
  return (
    <section>
      <h2>{passage.title}</h2>
      {passage.artist && <p>{passage.artist}</p>}
      <p>{passage.chords.join(" ")}</p>
      <RatingButtons onRate={rate(id, onDone)} />
    </section>
  );
}

function Challenge({ text, onDone, last }: { text: string } & Omit<StepProps, "rate">) {
  return (
    <section>
      <ChallengeCard text={text} />
      <button type="button" onClick={onDone}>
        {last ? "Finish" : "Next"}
      </button>
    </section>
  );
}

function LessonStep({ quality, card, rate, onDone, last }: { quality: Quality; card: string } & StepProps) {
  const lesson = useLesson(quality);
  const [rated, setRated] = useState(0);
  const next = () => setRated(rated + 1);
  if (!lesson) return <p>Loading…</p>;
  if (rated === 3) return <PassageStep id={`passage:${lesson.passages[0]}`} rate={rate} onDone={next} />;
  if (rated > 3) return <Challenge text={card} onDone={onDone} last={last} />;
  return (
    <section>
      <h2>{quality}</h2>
      <p>{lesson.explanation}</p>
      {lesson.shapes.map((shape, i) => (
        <figure key={i}>
          <Fretboard positions={positions(shape, i)} />
          <figcaption>{INVERSIONS[i]}</figcaption>
        </figure>
      ))}
      <p>Rate the {INVERSIONS[rated]}</p>
      <RatingButtons key={rated} onRate={rate(`shape:${quality}:${rated}`, next)} />
    </section>
  );
}

function Step({ step, rate, onDone, last }: { step: Schemas["Step"] } & StepProps) {
  const onRate = rate(step.id, onDone);
  switch (step.kind) {
    case "review":
      return step.root ? (
        <ShapeReview id={step.id} root={step.root} onRate={onRate} />
      ) : (
        <PassageReview id={step.id} onRate={onRate} />
      );
    case "lesson":
      return <LessonStep quality={step.id as Quality} card={step.card ?? ""} rate={rate} onDone={onDone} last={last} />;
    case "passage":
      return <PassageStep id={step.id} rate={rate} onDone={onDone} />;
    case "challenge":
      return <Challenge text={step.card ?? ""} onDone={onDone} last={last} />;
  }
}

function Summary({ summary }: { summary: Schemas["Summary"] }) {
  return (
    <section>
      <h2>Summary</h2>
      <p>
        Practiced for <strong>{format(summary.duration_seconds)}</strong>
      </p>
      <p>{summary.items_rated} items rated</p>
      <p>{summary.streak}-day streak</p>
      <h3>Next due</h3>
      <ul>
        {summary.next_due.map((item) => (
          <li key={item.id}>
            {item.id}: box {item.box}, due {new Date(item.due_at).toLocaleDateString()}
          </li>
        ))}
      </ul>
      <Link to="/">Home</Link>
    </section>
  );
}

function Run({ plan, length }: Started) {
  // Theory questions have no screen yet, so they're skipped rather than stalling the session.
  const steps = plan.steps.filter((step) => step.kind !== "theory");
  const [index, setIndex] = useState(0);
  const [summary, setSummary] = useState<Schemas["Summary"]>();
  const [failed, setFailed] = useState(false);
  const path = { id: plan.id };

  const finish = async () => {
    const result = await api.post("/api/sessions/{id}/finish", { path });
    setFailed(!result.ok);
    if (result.ok) setSummary(result.data);
  };
  const rate: Rate = (item_id, then) => async (rating) => {
    const result = await api.post("/api/sessions/{id}/ratings", { path, body: { item_id, rating } });
    setFailed(!result.ok);
    if (result.ok) then();
  };
  const last = index === steps.length - 1;

  if (summary) return <Summary summary={summary} />;
  return (
    <main>
      <Timer mode={length === "25" ? "countdown" : "countup"} onWrapUp={finish} />
      {failed && <p role="alert">Couldn't reach the server. Try again.</p>}
      {steps.length ? (
        <Step key={index} step={steps[index]} rate={rate} onDone={last ? finish : () => setIndex(index + 1)} last={last} />
      ) : (
        <button type="button" onClick={finish}>
          Finish
        </button>
      )}
    </main>
  );
}

export default function Session() {
  const started = useStarted();
  return started ? <Run {...started} /> : <p>No session in progress.</p>;
}
