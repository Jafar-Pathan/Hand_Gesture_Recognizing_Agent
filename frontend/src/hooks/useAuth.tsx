/**
 * useAuth — Authentication React context.
 *
 * Provides: user, login(), register(), logout(), isAuthenticated, isLoading
 * Persists JWT tokens in localStorage and restores session on mount.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { authApi, TokenStore, type UserOut } from '../api/client';

// ── Types ────────────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: UserOut | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

// ── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session from stored token on mount
  useEffect(() => {
    const token = TokenStore.getAccess();
    if (!token) {
      setIsLoading(false);
      return;
    }

    authApi
      .me()
      .then(({ data }) => setUser(data))
      .catch(() => {
        // Token invalid/expired — clear storage
        TokenStore.clear();
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    try {
      const { data } = await authApi.login(email, password);
      TokenStore.set(data.access_token, data.refresh_token);
      setUser(data.user);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Login failed. Please check your credentials.';
      throw new Error(message);
    }
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string): Promise<void> => {
      try {
        const { data } = await authApi.register(username, email, password);
        // Don't auto-login — redirect to /login after register
        TokenStore.clear();
        void data; // discard tokens; user will login manually
      } catch (err: unknown) {
        const message =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Registration failed. Please try again.';
        throw new Error(message);
      }
    },
    [],
  );

  const logout = useCallback((): void => {
    TokenStore.clear();
    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>.');
  }
  return ctx;
}
