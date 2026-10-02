import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

// Dummy auth — open access, no real signup/login required
interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string;
  role: "member";
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<{ error: string | null }>;
  signup: (email: string, password: string, fullName: string) => Promise<{ error: string | null }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const GUEST_USER: User = {
  id: "guest",
  email: "guest@planetive.local",
  full_name: "Guest User",
  role: "member",
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Always signed in as guest — no login wall
    setUser(GUEST_USER);
    setIsLoading(false);
  }, []);

  const login = async (_email: string, _password: string) => {
    setUser(GUEST_USER);
    return { error: null };
  };

  const signup = async (_email: string, _password: string, _fullName: string) => {
    setUser(GUEST_USER);
    return { error: null };
  };

  const logout = () => {
    // Stay as guest — app is open access
    setUser(GUEST_USER);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: true,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
