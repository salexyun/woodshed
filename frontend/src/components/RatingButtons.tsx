const RATINGS = ["easy", "challenging", "unfamiliar"] as const;

export type Rating = (typeof RATINGS)[number];

export default function RatingButtons({ onRate }: { onRate: (rating: Rating) => void }) {
  return (
    <div>
      {RATINGS.map((rating) => (
        <button key={rating} type="button" onClick={() => onRate(rating)}>
          {rating}
        </button>
      ))}
    </div>
  );
}
