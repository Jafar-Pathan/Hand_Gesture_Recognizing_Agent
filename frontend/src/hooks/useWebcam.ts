/**
 * useWebcam — React hook for webcam access and frame capture.
 *
 * Provides:
 *   - videoRef      — attach to <video> element
 *   - isActive      — whether camera is running
 *   - error         — camera access error message (or null)
 *   - startCamera() — request getUserMedia and begin streaming
 *   - stopCamera()  — stop all tracks
 *   - captureFrame()— draw current frame to canvas, return base64 JPEG
 */

import React, { useCallback, useRef, useState } from 'react';

export interface WebcamHook {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  isActive: boolean;
  error: string | null;
  startCamera: () => Promise<void>;
  stopCamera: () => void;
  captureFrame: () => string | null;
}

export function useWebcam(): WebcamHook {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startCamera = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setIsActive(true);
    } catch (err) {
      const msg =
        err instanceof DOMException
          ? err.name === 'NotAllowedError'
            ? 'Camera permission denied. Please allow camera access in your browser.'
            : err.name === 'NotFoundError'
              ? 'No camera found on this device.'
              : `Camera error: ${err.message}`
          : 'Failed to access the camera.';
      setError(msg);
      setIsActive(false);
    }
  }, []);

  const stopCamera = useCallback((): void => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsActive(false);
  }, []);

  const captureFrame = useCallback((): string | null => {
    const video = videoRef.current;
    if (!video || !isActive || video.readyState < 2) return null;

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    // Return as JPEG base64 (with data-URL prefix stripped)
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    return dataUrl; // keep prefix — backend will strip it
  }, [isActive]);

  return { videoRef, isActive, error, startCamera, stopCamera, captureFrame };
}
