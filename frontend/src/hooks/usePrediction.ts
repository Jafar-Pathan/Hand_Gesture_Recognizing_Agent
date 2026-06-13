/**
 * usePrediction — React hook for gesture inference state management.
 *
 * Provides:
 *   - currentPrediction — latest gesture result (or null)
 *   - history           — up to 50 recent predictions
 *   - fps               — rolling average frames-per-second
 *   - isProcessing      — whether a request is in-flight
 *   - sendPrediction()  — send base64 image to /predict API
 */

import { useCallback, useRef, useState } from 'react';
import { predictApi } from '../api/client';

export interface PredictionItem {
  gesture: string;
  confidence: number;
  allScores: Record<string, number>;
  mode: string;
  inference_ms: number | null;
  timestamp: string;
}

export interface PredictionHook {
  currentPrediction: PredictionItem | null;
  history: PredictionItem[];
  fps: number;
  isProcessing: boolean;
  sendPrediction: (base64: string) => Promise<void>;
}

const MAX_HISTORY = 50;
const FPS_WINDOW = 10; // frames to average over

export function usePrediction(): PredictionHook {
  const [currentPrediction, setCurrentPrediction] = useState<PredictionItem | null>(null);
  const [history, setHistory] = useState<PredictionItem[]>([]);
  const [fps, setFps] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  // FPS tracking
  const frameTimestamps = useRef<number[]>([]);

  const _updateFps = useCallback(() => {
    const now = performance.now();
    const window = frameTimestamps.current;
    window.push(now);
    if (window.length > FPS_WINDOW) {
      window.splice(0, window.length - FPS_WINDOW);
    }
    if (window.length >= 2) {
      const elapsed = (now - window[0]) / 1000; // seconds
      setFps((window.length - 1) / elapsed);
    }
  }, []);

  const sendPrediction = useCallback(
    async (base64: string): Promise<void> => {
      if (isProcessing) return; // drop frame if previous is still in-flight
      setIsProcessing(true);

      try {
        const { data } = await predictApi.predict(base64);

        const item: PredictionItem = {
          gesture: data.gesture,
          confidence: data.confidence,
          allScores: data.all_scores,
          mode: data.mode,
          inference_ms: data.inference_ms,
          timestamp: data.timestamp,
        };

        setCurrentPrediction(item);
        setHistory((prev: PredictionItem[]) => [item, ...prev].slice(0, MAX_HISTORY));
        _updateFps();
      } catch (err) {
        // Silently swallow prediction errors (e.g. model not loaded, network blip)
        // so the camera feed keeps running
        console.warn('[usePrediction] Prediction failed:', err);
      } finally {
        setIsProcessing(false);
      }
    },
    [isProcessing, _updateFps],
  );

  return { currentPrediction, history, fps, isProcessing, sendPrediction };
}
