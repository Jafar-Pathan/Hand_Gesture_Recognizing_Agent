/**
 * Axios API client for the Hand Gesture Recognition backend.
 *
 * - Base URL: VITE_API_URL env var (falls back to http://localhost:8000)
 * - Attaches Bearer token from localStorage on every request
 * - On 401: attempts token refresh, retries the original request
 * - On refresh failure: clears tokens and reloads to /login
 */

import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

const BASE_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000') + '/api/v1';

const client = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

// ── Token storage helpers ────────────────────────────────────────────────────

export const TokenStore = {
  getAccess: (): string | null => localStorage.getItem('access_token'),
  getRefresh: (): string | null => localStorage.getItem('refresh_token'),
  set: (access: string, refresh: string): void => {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  },
  clear: (): void => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// ── Request interceptor — attach Bearer token ────────────────────────────────

client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = TokenStore.getAccess();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Response interceptor — auto-refresh on 401 ──────────────────────────────

let _isRefreshing = false;
let _refreshQueue: Array<(token: string) => void> = [];

function _onRefreshed(newToken: string) {
  _refreshQueue.forEach((cb) => cb(newToken));
  _refreshQueue = [];
}

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Only intercept 401 on non-auth endpoints and only once
    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url?.includes('/auth/')
    ) {
      if (_isRefreshing) {
        // Queue requests that arrive while refresh is in progress
        return new Promise((resolve) => {
          _refreshQueue.push((token: string) => {
            original.headers['Authorization'] = `Bearer ${token}`;
            resolve(client(original));
          });
        });
      }

      original._retry = true;
      _isRefreshing = true;

      const refreshToken = TokenStore.getRefresh();
      if (!refreshToken) {
        TokenStore.clear();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        TokenStore.set(data.access_token, data.refresh_token);
        _onRefreshed(data.access_token);
        original.headers['Authorization'] = `Bearer ${data.access_token}`;
        return client(original);
      } catch (_refreshError) {
        TokenStore.clear();
        window.location.href = '/login';
        return Promise.reject(_refreshError);
      } finally {
        _isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

export default client;

// ── Typed API helpers ────────────────────────────────────────────────────────

export interface UserOut {
  id: number;
  email: string;
  username: string;
  role: 'admin' | 'user';
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserOut;
}

export interface PredictResponse {
  gesture: string;
  confidence: number;
  all_scores: Record<string, number>;
  mode: string;
  inference_ms: number | null;
  timestamp: string;
}

export interface TrainStatusOut {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  backbone: string;
  epochs: number;
  batch_size: number;
  train_accuracy: number | null;
  val_accuracy: number | null;
  loss: number | null;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface StatsOut {
  total_users: number;
  total_predictions: number;
  total_training_jobs: number;
  predictions_today: number;
  active_users: number;
}

export const authApi = {
  register: (username: string, email: string, password: string) =>
    client.post<TokenResponse>('/auth/register', { username, email, password }),
  login: (email: string, password: string) =>
    client.post<TokenResponse>('/auth/login', { email, password }),
  me: () => client.get<UserOut>('/auth/me'),
};

export const predictApi = {
  predict: (image: string, mode?: string) =>
    client.post<PredictResponse>('/predict', { image, mode }),
  history: (page = 1, pageSize = 20) =>
    client.get('/predictions', { params: { page, page_size: pageSize } }),
};

export const trainingApi = {
  start: (backbone: string, epochs: number, batchSize: number) =>
    client.post<TrainStatusOut>('/training/start', {
      backbone,
      epochs,
      batch_size: batchSize,
    }),
  status: (jobId: string) => client.get<TrainStatusOut>(`/training/status/${jobId}`),
  history: (page = 1) => client.get('/training/history', { params: { page } }),
};

export const adminApi = {
  stats: () => client.get<StatsOut>('/admin/stats'),
  users: (page = 1) => client.get('/admin/users', { params: { page } }),
  deactivateUser: (userId: number) => client.delete(`/admin/users/${userId}`),
};
