import { type ReactNode, useState } from "react";

import RatingButtons, { type Rating } from "./RatingButtons";

type Props = { prompt: string; answer: ReactNode; onRate: (rating: Rating) => void };

export default function ReviewCard({ prompt, answer, onRate }: Props) {
  const [revealed, setRevealed] = useState(false);
  return (
    <section>
      <p>{prompt}</p>
      {revealed ? (
        <>
          {answer}
          <RatingButtons onRate={onRate} />
        </>
      ) : (
        <button type="button" onClick={() => setRevealed(true)}>
          Reveal
        </button>
      )}
    </section>
  );
}
