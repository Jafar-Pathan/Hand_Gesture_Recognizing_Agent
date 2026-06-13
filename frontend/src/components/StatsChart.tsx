/**
 * StatsChart — Recharts bar chart of gesture frequency counts.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { PredictionItem } from '../hooks/usePrediction';

interface StatsChartProps {
  history: PredictionItem[];
}

const GESTURE_COLORS: Record<string, string> = {
  Palm: '#3b82f6',
  L: '#a855f7',
  Fist: '#ef4444',
  'Fist Moved': '#f97316',
  Thumb: '#eab308',
  Index: '#22c55e',
  OK: '#14b8a6',
  'Palm Moved': '#6366f1',
  C: '#ec4899',
  Down: '#06b6d4',
};

interface ChartEntry {
  gesture: string;
  count: number;
  color: string;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ChartEntry }> }) {
  if (!active || !payload?.length) return null;
  const { gesture, count, color } = payload[0].payload;
  return (
    <div className="bg-gray-800 border border-gray-700/50 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-xs font-semibold" style={{ color }}>
        {gesture}
      </p>
      <p className="text-xs text-gray-400 mt-0.5">
        {count} prediction{count !== 1 ? 's' : ''}
      </p>
    </div>
  );
}

export default function StatsChart({ history }: StatsChartProps) {
  // Aggregate gesture counts
  const counts: Record<string, number> = {};
  for (const item of history) {
    counts[item.gesture] = (counts[item.gesture] ?? 0) + 1;
  }

  const data: ChartEntry[] = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([gesture, count]) => ({
      gesture: gesture.length > 8 ? gesture.slice(0, 7) + '…' : gesture,
      count,
      color: GESTURE_COLORS[gesture] ?? '#6b7280',
    }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40">
        <p className="text-gray-600 text-sm">No data yet — start detecting gestures</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey="gesture"
          tick={{ fill: '#6b7280', fontSize: 10 }}
          axisLine={{ stroke: '#374151' }}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fill: '#6b7280', fontSize: 10 }}
          axisLine={{ stroke: '#374151' }}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
