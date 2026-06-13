/**
 * ConfidenceBar — horizontal bar chart of per-class confidence scores.
 */

interface ConfidenceBarProps {
  scores: Record<string, number> | null;
  topGesture: string | null;
}

const GESTURE_ORDER = [
  'Palm', 'L', 'Fist', 'Fist Moved', 'Thumb',
  'Index', 'OK', 'Palm Moved', 'C', 'Down',
];

export default function ConfidenceBar({ scores, topGesture }: ConfidenceBarProps) {
  if (!scores) {
    return (
      <div className="flex flex-col gap-2.5 py-2">
        {GESTURE_ORDER.map((name) => (
          <div key={name} className="flex items-center gap-2">
            <span className="text-[11px] text-gray-500 w-20 shrink-0 text-right">{name}</span>
            <div className="flex-1 h-2 bg-gray-700/50 rounded-full" />
            <span className="text-[10px] text-gray-600 w-9 text-right font-mono">—</span>
          </div>
        ))}
      </div>
    );
  }

  // Sort by score descending for display
  const sortedEntries = GESTURE_ORDER.map((name) => ({
    name,
    score: scores[name] ?? 0,
  }));

  return (
    <div className="flex flex-col gap-2">
      {sortedEntries.map(({ name, score }) => {
        const isTop = name === topGesture;
        const pct = (score * 100).toFixed(1);
        const barWidth = `${(score * 100).toFixed(2)}%`;

        return (
          <div key={name} className="flex items-center gap-2.5 group">
            <span
              className={`text-[11px] w-20 shrink-0 text-right transition-colors ${
                isTop ? 'text-blue-400 font-semibold' : 'text-gray-500'
              }`}
            >
              {name}
            </span>
            <div className="flex-1 h-2 bg-gray-700/50 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  isTop
                    ? 'bg-gradient-to-r from-blue-500 to-blue-400'
                    : 'bg-gray-600/70'
                }`}
                style={{ width: barWidth }}
              />
            </div>
            <span
              className={`text-[10px] w-9 text-right font-mono transition-colors ${
                isTop ? 'text-blue-400 font-bold' : 'text-gray-600'
              }`}
            >
              {pct}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
