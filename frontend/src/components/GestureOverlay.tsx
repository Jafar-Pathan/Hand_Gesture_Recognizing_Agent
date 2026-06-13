/**
 * GestureOverlay — animated gesture result badge overlaid on the webcam feed.
 */

interface GestureOverlayProps {
  gesture: string;
  confidence: number;
}

const GESTURE_COLORS: Record<string, string> = {
  Palm: 'from-blue-500 to-blue-600',
  L: 'from-purple-500 to-purple-600',
  Fist: 'from-red-500 to-red-600',
  'Fist Moved': 'from-orange-500 to-orange-600',
  Thumb: 'from-yellow-500 to-yellow-600',
  Index: 'from-green-500 to-green-600',
  OK: 'from-teal-500 to-teal-600',
  'Palm Moved': 'from-indigo-500 to-indigo-600',
  C: 'from-pink-500 to-pink-600',
  Down: 'from-cyan-500 to-cyan-600',
};

export default function GestureOverlay({ gesture, confidence }: GestureOverlayProps) {
  const gradient = GESTURE_COLORS[gesture] ?? 'from-blue-500 to-blue-600';
  const pct = (confidence * 100).toFixed(1);

  return (
    <div className="absolute bottom-12 left-3 right-3 flex items-end justify-between pointer-events-none animate-fadeInUp">
      {/* Gesture name badge */}
      <div className={`bg-gradient-to-r ${gradient} rounded-xl px-4 py-2.5 shadow-xl backdrop-blur-sm`}>
        <p className="text-white font-bold text-xl tracking-tight leading-none">{gesture}</p>
        <p className="text-white/75 text-[11px] font-medium mt-0.5">Detected gesture</p>
      </div>

      {/* Confidence badge */}
      <div className="bg-black/60 backdrop-blur-md rounded-xl px-3 py-2 shadow-xl border border-white/10">
        <p className="text-white font-mono font-bold text-lg leading-none">{pct}%</p>
        <p className="text-gray-400 text-[10px] mt-0.5">confidence</p>
      </div>
    </div>
  );
}
