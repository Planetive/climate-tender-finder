import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

// User type - all users are members (no admin role)
interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string;
  role: "member"; // All users are members
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

// Mock users storage - all users are members
// In production, this would be stored in a database
const STORAGE_KEY = "funding_tracker_users";
const getStoredUsers = (): User[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

const saveUsers = (users: User[]) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(users));
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session in localStorage
    const storedUser = localStorage.getItem("auth_user");
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string): Promise<{ error: string | null }> => {
    // Simple login - check if user exists and password is valid
    const users = getStoredUsers();
    const foundUser = users.find((u) => u.email === email);
    
    if (!foundUser) {
      return { error: "Invalid email or password" };
    }
    
    // In a real app, you'd verify the password hash here
    // For now, we just check password length (password is stored in localStorage for demo)
    const userPassword = localStorage.getItem(`user_password_${email}`);
    if (password.length < 6 || (userPassword && password !== userPassword)) {
      return { error: "Invalid email or password" };
    }
    
    setUser(foundUser);
    localStorage.setItem("auth_user", JSON.stringify(foundUser));
    return { error: null };
  };

  const signup = async (email: string, password: string, fullName: string): Promise<{ error: string | null }> => {
    // Validate input
    if (password.length < 6) {
      return { error: "Password must be at least 6 characters" };
    }
    
    if (!fullName.trim()) {
      return { error: "Please enter your full name" };
    }
    
    // Check if user already exists
    const users = getStoredUsers();
    if (users.find((u) => u.email === email)) {
      return { error: "User with this email already exists" };
    }
    
    // Create new user (all users are members)
    const newUser: User = {
      id: `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      email,
      full_name: fullName.trim(),
      role: "member", // All users are members
    };
    
    // Save user and password
    users.push(newUser);
    saveUsers(users);
    localStorage.setItem(`user_password_${email}`, password); // In production, hash this!
    
    // Auto-login after signup
    setUser(newUser);
    localStorage.setItem("auth_user", JSON.stringify(newUser));
    return { error: null };
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("auth_user");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
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
