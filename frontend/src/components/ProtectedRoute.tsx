import { ReactNode } from "react";

/**
 * Open-access wrapper — auth is disabled; anyone can view the app.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
