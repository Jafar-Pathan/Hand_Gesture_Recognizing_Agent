import { useState, useCallback } from 'react';
import { LogOut, Activity, Download } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useWebcam } from '../hooks/useWebcam';
import { usePrediction } from '../hooks/usePrediction';
import Webcam from '../components/Webcam';
import GestureOverlay from '../components/GestureOverlay';
import ConfidenceBar from '../components/ConfidenceBar';
import PredictionHistory from '../components/PredictionHistory';
import StatsChart from '../components/StatsChart';
import AdminPanel from '../components/AdminPanel';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const { videoRef, isActive, error: webcamError, startCamera, stopCamera, captureFrame } = useWebcam();
  const { currentPrediction, history, fps, isProcessing, sendPrediction } = usePrediction();
  const [captureInterval, setCaptureInterval] = useState(500);

  const handleCapture = useCallback(
    async (base64: string) => {
      await sendPrediction(base64);
    },
    [sendPrediction]
  );

  const handleExportCSV = useCallback(() => {
    if (history.length === 0) return;

    const headers = ['#', 'Gesture', 'Confidence', 'Mode', 'Time'];
    const rows = history.map((item, index) => [
      index + 1,
      item.gesture,
      (item.confidence * 100).toFixed(1) + '%',
      item.mode,
      new Date(item.timestamp).toLocaleString(),
    ]);

    const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `gesture_predictions_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [history]);

  return (
    <div className="min-h-screen bg-gray-900 dark-scrollbar">
      {/* Header */}
      <header className="bg-gray-800/80 backdrop-blur-md border-b border-gray-700/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-bold text-white">
              <span className="text-blue-400">Gesture</span> Dashboard
            </h1>
            {/* FPS Badge */}
            <div className="flex items-center gap-1.5 bg-gray-700/50 border border-gray-600/30 rounded-full px-3 py-1">
              <Activity className="w-3.5 h-3.5 text-green-400" />
              <span className="text-xs font-mono text-green-400">{fps.toFixed(1)} FPS</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* User info */}
            <div className="hidden sm:flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                <span className="text-xs font-bold text-blue-400">
                  {user?.username?.charAt(0).toUpperCase() ?? 'U'}
                </span>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-200">{user?.username ?? 'User'}</p>
                <p className="text-[10px] text-gray-500">{user?.role ?? 'user'}</p>
              </div>
            </div>

            {/* Export CSV */}
            <button
              onClick={handleExportCSV}
              disabled={history.length === 0}
              className="flex items-center gap-1.5 bg-gray-700/50 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed border border-gray-600/30 rounded-lg px-3 py-1.5 text-xs text-gray-300 hover:text-white transition-all"
            >
              <Download className="w-3.5 h-3.5" />
              Export CSV
            </button>

            {/* Logout */}
            <button
              onClick={logout}
              className="flex items-center gap-1.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-lg px-3 py-1.5 text-xs text-red-400 hover:text-red-300 transition-all"
            >
              <LogOut className="w-3.5 h-3.5" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Top row: Webcam + Confidence */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Webcam Panel */}
          <div className="bg-gray-800/60 border border-gray-700/40 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-4 border-b border-gray-700/30 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-200">Live Camera Feed</h2>
              <div className="flex items-center gap-2">
                <label className="text-[10px] text-gray-500">
                  Interval:
                  <select
                    value={captureInterval}
                    onChange={(e) => setCaptureInterval(Number(e.target.value))}
                    className="ml-1 bg-gray-700 border border-gray-600 rounded px-1 py-0.5 text-[10px] text-gray-300"
                  >
                    <option value={250}>250ms</option>
                    <option value={500}>500ms</option>
                    <option value={1000}>1s</option>
                    <option value={2000}>2s</option>
                  </select>
                </label>
              </div>
            </div>
            <div className="relative aspect-video bg-black">
              <Webcam
                videoRef={videoRef}
                isActive={isActive}
                error={webcamError}
                onCapture={handleCapture}
                captureInterval={captureInterval}
                startCamera={startCamera}
                stopCamera={stopCamera}
                captureFrame={captureFrame}
              />
              {currentPrediction && (
                <GestureOverlay
                  gesture={currentPrediction.gesture}
                  confidence={currentPrediction.confidence}
                />
              )}
            </div>
          </div>

          {/* Right column: Confidence + Current Prediction */}
          <div className="space-y-6">
            {/* Current prediction */}
            <div className="bg-gray-800/60 border border-gray-700/40 rounded-2xl p-6 shadow-xl">
              <h2 className="text-sm font-semibold text-gray-200 mb-4">Current Prediction</h2>
              {currentPrediction ? (
                <div className="text-center">
                  <p className="text-5xl font-bold text-white mb-2">{currentPrediction.gesture}</p>
                  <p className="text-2xl font-mono text-blue-400">
                    {(currentPrediction.confidence * 100).toFixed(1)}%
                  </p>
                  {isProcessing && (
                    <div className="mt-3 flex items-center justify-center gap-2">
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                      <span className="text-xs text-gray-400">Processing...</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500 text-sm">No prediction yet</p>
                  <p className="text-gray-600 text-xs mt-1">Start the camera to begin detecting gestures</p>
                </div>
              )}
            </div>

            {/* Confidence Bars */}
            <div className="bg-gray-800/60 border border-gray-700/40 rounded-2xl p-6 shadow-xl">
              <h2 className="text-sm font-semibold text-gray-200 mb-4">Confidence Distribution</h2>
              <ConfidenceBar scores={currentPrediction?.allScores ?? null} topGesture={currentPrediction?.gesture ?? null} />
            </div>
          </div>
        </div>

        {/* Stats and History */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-gray-800/60 border border-gray-700/40 rounded-2xl p-6 shadow-xl">
            <h2 className="text-sm font-semibold text-gray-200 mb-4">Gesture Frequency</h2>
            <StatsChart history={history} />
          </div>

          <div className="bg-gray-800/60 border border-gray-700/40 rounded-2xl p-6 shadow-xl">
            <h2 className="text-sm font-semibold text-gray-200 mb-4">Prediction History</h2>
            <PredictionHistory history={history} onExport={handleExportCSV} />
          </div>
        </div>

        {/* Admin Panel */}
        {user?.role === 'admin' && (
          <div className="bg-gray-800/60 border border-gray-700/40 rounded-2xl p-6 shadow-xl">
            <AdminPanel />
          </div>
        )}
      </main>
    </div>
  );
}
