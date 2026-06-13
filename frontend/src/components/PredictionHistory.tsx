/**
 * PredictionHistory — scrollable list of past gesture predictions.
 */

import { Download, Clock } from 'lucide-react';
import type { PredictionItem } from '../hooks/usePrediction';

interface PredictionHistoryProps {
  history: PredictionItem[];
  onExport: () => void;
}

function timeAgo(timestamp: string): string {
  const diff = (Date.now() - new Date(timestamp).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

const BADGE_COLORS: Record<string, string> = {
  Palm: 'bg-blue-500/20 text-blue-400',
  L: 'bg-purple-500/20 text-purple-400',
  Fist: 'bg-red-500/20 text-red-400',
  'Fist Moved': 'bg-orange-500/20 text-orange-400',
  Thumb: 'bg-yellow-500/20 text-yellow-400',
  Index: 'bg-green-500/20 text-green-400',
  OK: 'bg-teal-500/20 text-teal-400',
  'Palm Moved': 'bg-indigo-500/20 text-indigo-400',
  C: 'bg-pink-500/20 text-pink-400',
  Down: 'bg-cyan-500/20 text-cyan-400',
};

export default function PredictionHistory({ history, onExport }: PredictionHistoryProps) {
  if (history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 gap-3">
        <Clock className="w-8 h-8 text-gray-600" />
        <p className="text-gray-500 text-sm">No predictions yet</p>
        <p className="text-gray-600 text-xs">Start the camera to begin detecting gestures</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-gray-500">{history.length} predictions</span>
        <button
          onClick={onExport}
          className="flex items-center gap-1 text-[11px] text-gray-500 hover:text-gray-300 transition-colors"
        >
          <Download className="w-3 h-3" />
          Export
        </button>
      </div>

      <div className="overflow-y-auto max-h-56 space-y-1.5 pr-1 dark-scrollbar">
        {history.map((item, idx) => {
          const colorClass = BADGE_COLORS[item.gesture] ?? 'bg-gray-500/20 text-gray-400';
          return (
            <div
              key={`${item.timestamp}-${idx}`}
              className="flex items-center gap-3 bg-gray-700/30 hover:bg-gray-700/50 rounded-lg px-3 py-2 transition-colors"
            >
              {/* Rank */}
              <span className="text-[10px] text-gray-600 w-5 text-center font-mono">
                {history.length - idx}
              </span>

              {/* Gesture badge */}
              <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${colorClass}`}>
                {item.gesture}
              </span>

              {/* Confidence */}
              <span className="text-xs font-mono text-gray-300 ml-auto">
                {(item.confidence * 100).toFixed(1)}%
              </span>

              {/* Mode */}
              <span className="text-[10px] text-gray-600 bg-gray-700/50 px-1.5 py-0.5 rounded">
                {item.mode}
              </span>

              {/* Time */}
              <span className="text-[10px] text-gray-600 w-12 text-right">
                {timeAgo(item.timestamp)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
