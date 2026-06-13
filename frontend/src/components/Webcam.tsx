/**
 * Webcam — live camera feed component.
 *
 * Renders a <video> element, start/stop button, error message,
 * and fires onCapture(base64) on the configured captureInterval.
 */

import React, { useEffect, useRef } from 'react';
import { Camera, CameraOff, Loader2 } from 'lucide-react';

interface WebcamProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  isActive: boolean;
  error: string | null;
  onCapture: (base64: string) => void;
  captureInterval: number;
  startCamera: () => Promise<void>;
  stopCamera: () => void;
  captureFrame: () => string | null;
}

export default function Webcam({
  videoRef,
  isActive,
  error,
  onCapture,
  captureInterval,
  startCamera,
  stopCamera,
  captureFrame,
}: WebcamProps) {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Set up / tear down capture interval whenever active state or interval changes
  useEffect(() => {
    if (!isActive) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    intervalRef.current = setInterval(() => {
      const frame = captureFrame();
      if (frame) onCapture(frame);
    }, captureInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isActive, captureInterval, captureFrame, onCapture]);

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center bg-black">
      {/* Video element — always present so videoRef is stable */}
      <video
        ref={videoRef as React.RefObject<HTMLVideoElement>}
        autoPlay
        playsInline
        muted
        className={`w-full h-full object-cover transition-opacity duration-300 ${
          isActive ? 'opacity-100' : 'opacity-0'
        }`}
      />

      {/* Placeholder when not active */}
      {!isActive && !error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
          <div className="w-20 h-20 rounded-full bg-gray-700/50 flex items-center justify-center border border-gray-600/30">
            <Camera className="w-9 h-9 text-gray-500" />
          </div>
          <p className="text-gray-400 text-sm">Camera is off</p>
          <p className="text-gray-600 text-xs">Click Start Camera to begin</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6">
          <CameraOff className="w-10 h-10 text-red-400" />
          <p className="text-red-400 text-sm text-center">{error}</p>
        </div>
      )}

      {/* Control button — bottom center overlay */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2">
        {isActive ? (
          <button
            onClick={stopCamera}
            className="flex items-center gap-2 bg-red-500/80 hover:bg-red-500 backdrop-blur-sm border border-red-400/30 rounded-full px-4 py-2 text-xs font-medium text-white transition-all duration-200 shadow-lg"
          >
            <CameraOff className="w-3.5 h-3.5" />
            Stop Camera
          </button>
        ) : (
          <button
            onClick={startCamera}
            className="flex items-center gap-2 bg-blue-600/80 hover:bg-blue-600 backdrop-blur-sm border border-blue-400/30 rounded-full px-4 py-2 text-xs font-medium text-white transition-all duration-200 shadow-lg"
          >
            <Camera className="w-3.5 h-3.5" />
            Start Camera
          </button>
        )}
      </div>

      {/* Live indicator */}
      {isActive && (
        <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/50 backdrop-blur-sm rounded-full px-2.5 py-1">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-[10px] font-semibold text-white tracking-wider">LIVE</span>
        </div>
      )}
    </div>
  );
}
