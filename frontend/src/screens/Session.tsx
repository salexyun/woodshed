import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useParams } from "react-router";

import { api, type ApiError, type ApiResult } from "../api";
import type { components } from "../api-schema";
import ChallengeCard from "../components/ChallengeCard";
import Fretboard, { type Position } from "../components/Fretboard";
import RatingButtons, { type Rating } from "../components/RatingButtons";
import ReviewCard from "../components/ReviewCard";
import Timer, { format } from "../components/Timer";

type Schemas = components["schemas"];
type Quality = Schemas["Lesson"]["quality"];
type Failed = { ok: false; error: ApiError };
// Builds the rating handler for one item; `then` runs once the rating is saved.
type Rate = (itemId: string, then: () => void) => (rating: Rating) => void;
// `done` counts the items a resumed lesson already rated.
type StepProps = { rate: Rate; onDone: () => void; last: boolean; done: number };

const INVERSIONS = ["root position", "1st inversion", "2nd inversion"];
// Shapes are given low to high on strings 3-2-1; each inversion puts the root on a different string.
const ROOT_STRING = [3, 1, 2];
const SEMITONES: Record<string, number> = {
  C: 0, "C♯": 1, "D♭": 1, D: 2, "E♭": 3, E: 4, F: 5,
  "F♯": 6, "G♭": 6, G: 7, "A♭": 8, A: 9, "B♭": 10, B: 11,
};

// Each step is keyed, so it remounts and loads once.
function useLoad<T>(load: () => Promise<ApiResult<T>>): ApiResult<T> | undefined {
  const [result, setResult] = useState<ApiResult<T>>();
  useEffect(() => {
    load().then(setResult);
  }, []);
  return result;
}

// Retrying can't fix a 409: the session was finished, e.g. by Wrap up while a rating was in flight.
const Alert = ({ error }: { error: ApiError }) => (
  <p role="alert">
    {error.kind === "http" && error.status === 409
      ? "This session is finished."
      : "Couldn't reach the server. Try again."}
  </p>
);

const Pending = ({ result }: { result?: Failed }) => (result ? <Alert error={result.error} /> : <p>Loading…</p>);

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
  const lesson = useLesson(quality);
  if (!lesson?.ok) return <Pending result={lesson} />;
  const shape = lesson.data.shapes[Number(inversion)];
  return (
    <ReviewCard
      prompt={`Play ${root} ${quality}, ${INVERSIONS[Number(inversion)]}, on G-B-E`}
      answer={<Fretboard positions={positions(transpose(shape, root), Number(inversion))} />}
      onRate={onRate}
    />
  );
}

function PassageReview({ id, onRate }: { id: string; onRate: (r: Rating) => void }) {
  const result = usePassage(id);
  if (!result?.ok) return <Pending result={result} />;
  const passage = result.data;
  return (
    <ReviewCard prompt={`Play ${passage.title}`} answer={<p>{passage.chords.join(" ")}</p>} onRate={onRate} />
  );
}

function PassageStep({ id, rate, onDone }: { id: string } & Pick<StepProps, "rate" | "onDone">) {
  const result = usePassage(id);
  if (!result?.ok) return <Pending result={result} />;
  const passage = result.data;
  return (
    <section>
      <h2>{passage.title}</h2>
      {passage.artist && <p>{passage.artist}</p>}
      <p>{passage.chords.join(" ")}</p>
      <RatingButtons onRate={rate(id, onDone)} />
    </section>
  );
}

function Challenge({ text, onDone, last }: { text: string } & Pick<StepProps, "onDone" | "last">) {
  return (
    <section>
      <ChallengeCard text={text} />
      <button type="button" onClick={onDone}>
        {last ? "Finish" : "Next"}
      </button>
    </section>
  );
}

type LessonProps = { quality: Quality; card: string } & StepProps;

function LessonStep(props: LessonProps) {
  const result = useLesson(props.quality);
  if (!result?.ok) return <Pending result={result} />;
  return <LessonBody lesson={result.data} {...props} />;
}

// A lesson rates its 3 shapes, then its first passage, then shows its challenge card.
function LessonBody({ lesson, quality, card, rate, onDone, last, done }: { lesson: Schemas["Lesson"] } & LessonProps) {
  const [rated, setRated] = useState(done);
  const next = () => setRated(rated + 1);
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

function Step({ step, rate, onDone, last, done }: { step: Schemas["Step"] } & StepProps) {
  const onRate = rate(step.id, onDone);
  switch (step.kind) {
    case "review":
      return step.root ? (
        <ShapeReview id={step.id} root={step.root} onRate={onRate} />
      ) : (
        <PassageReview id={step.id} onRate={onRate} />
      );
    case "lesson":
      return (
        <LessonStep
          quality={step.id as Quality}
          card={step.card ?? ""}
          rate={rate}
          onDone={onDone}
          last={last}
          done={done}
        />
      );
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

const LESSON_ITEMS = 4; // 3 shapes and a passage

// Ratings arrive in plan order, so count them off step by step rather than matching ids:
// the same item can come due as a review before the lesson that rates it again.
function resumeAt(steps: Schemas["Step"][], rated: number) {
  for (const [index, step] of steps.entries()) {
    if (step.kind === "lesson" ? rated <= LESSON_ITEMS : rated === 0) return { index, done: rated };
    rated -= step.kind === "lesson" ? LESSON_ITEMS : step.kind === "challenge" ? 0 : 1;
  }
  return { index: steps.length, done: 0 };
}

function Run({ session }: { session: Schemas["SessionDetail"] }) {
  // Theory questions have no screen yet, so they're skipped rather than stalling the session.
  const steps = session.steps.filter((step) => step.kind !== "theory");
  const [resume] = useState(() => resumeAt(steps, session.rated.length));
  const [index, setIndex] = useState(resume.index);
  const [summary, setSummary] = useState<Schemas["Summary"]>();
  const [error, setError] = useState<ApiError>();
  // A ref, not state, so a second tap in the same frame already sees the first one's request.
  const pending = useRef(false);
  // State as well, so Wrap up is disabled rather than dropped while a request is out.
  const [busy, setBusy] = useState(false);
  const path = { id: session.id };

  async function send<T>(request: () => Promise<ApiResult<T>>, then: (data: T) => void) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    const result = await request();
    pending.current = false;
    setBusy(false);
    setError(result.ok ? undefined : result.error);
    if (result.ok) then(result.data);
  }
  const finish = () => send(() => api.post("/api/sessions/{id}/finish", { path }), setSummary);
  const rate: Rate = (item_id, then) => (rating) =>
    send(() => api.post("/api/sessions/{id}/ratings", { path, body: { item_id, rating } }), then);
  const last = index === steps.length - 1;

  if (summary) return <Summary summary={summary} />;
  return (
    <main>
      <Timer mode={session.length === "25" ? "countdown" : "countup"} onWrapUp={finish} busy={busy} />
      {error && <Alert error={error} />}
      {index < steps.length ? (
        <Step
          key={index}
          step={steps[index]}
          rate={rate}
          // Move past the last step before finishing, so a failed finish leaves only Finish to retry.
          onDone={() => (setIndex(index + 1), last && finish())}
          last={last}
          done={index === resume.index ? resume.done : 0}
        />
      ) : (
        <button type="button" onClick={finish}>
          Finish
        </button>
      )}
    </main>
  );
}

export default function Session() {
  const id = Number(useParams().id);
  const result = useLoad(() => api.get("/api/sessions/{id}", { path: { id } }));
  if (!result?.ok) return <Pending result={result} />;
  // A finished session has nothing left to do, and its summary was shown when it finished.
  if (result.data.finished_at) return <Navigate to="/" replace />;
  return <Run session={result.data} />;
}
