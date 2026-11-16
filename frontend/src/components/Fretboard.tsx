// Standard numbering: 1 is high E, 6 is low E.
type GuitarString = 1 | 2 | 3 | 4 | 5 | 6;

export type Position = { string: GuitarString; fret: number; root?: boolean };

const STRINGS: GuitarString[] = [6, 5, 4, 3, 2, 1]; // low E on the left
const FRETS = 5; // triad shapes span at most 4 frets
const STRING_GAP = 32;
const FRET_GAP = 36;
const MARGIN = 28;
const WIDTH = 2 * MARGIN + (STRINGS.length - 1) * STRING_GAP;
const HEIGHT = 2 * MARGIN + FRETS * FRET_GAP;

export default function Fretboard({ positions }: { positions: Position[] }) {
  // An empty board starts at the nut instead of Math.min()'s Infinity.
  const lowest = positions.length
    ? Math.min(...positions.map((p) => p.fret))
    : 0;
  const first = Math.max(lowest, 1);
  const x = (string: GuitarString) =>
    MARGIN + STRINGS.indexOf(string) * STRING_GAP;
  // Open strings sit on the nut; fretted notes sit midway between fret wires.
  const y = (fret: number) =>
    fret === 0 ? MARGIN : MARGIN + (fret - first + 0.5) * FRET_GAP;

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width={WIDTH}
      height={HEIGHT}
      role="img"
      aria-label="Fretboard"
      stroke="currentColor"
      fill="currentColor"
    >
      {Array.from({ length: FRETS + 1 }, (_, i) => (
        <line
          key={i}
          x1={MARGIN}
          x2={WIDTH - MARGIN}
          y1={MARGIN + i * FRET_GAP}
          y2={MARGIN + i * FRET_GAP}
        />
      ))}
      {lowest === 0 ? (
        <line
          data-testid="nut"
          x1={MARGIN}
          x2={WIDTH - MARGIN}
          y1={MARGIN}
          y2={MARGIN}
          strokeWidth={5}
        />
      ) : (
        <text
          data-testid="start-fret"
          x={MARGIN - 10}
          y={y(first)}
          stroke="none"
          textAnchor="end"
          dominantBaseline="middle"
          fontSize={14}
        >
          {first}
        </text>
      )}
      {STRINGS.map((string) => (
        <line
          key={string}
          data-testid="string"
          x1={x(string)}
          x2={x(string)}
          y1={MARGIN}
          y2={HEIGHT - MARGIN}
        />
      ))}
      {STRINGS.filter((s) => !positions.some((p) => p.string === s)).map(
        (string) => (
          <text
            key={string}
            data-testid="muted"
            data-string={string}
            x={x(string)}
            y={MARGIN - 12}
            stroke="none"
            textAnchor="middle"
            fontSize={14}
          >
            x
          </text>
        ),
      )}
      {positions.map(({ string, fret, root = false }) => (
        <g
          key={string}
          data-testid="dot"
          data-string={string}
          data-fret={fret}
          data-root={root}
          transform={`translate(${x(string)} ${y(fret)})`}
        >
          <circle r={9} />
          {root && <circle r={13} fill="none" />}
        </g>
      ))}
    </svg>
  );
}
