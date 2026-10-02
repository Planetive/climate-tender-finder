import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Alert } from "@/data/alerts";
import { fetchOpportunities, type Opportunity } from "@/services/api";
import { differenceInDays, formatDistanceToNow, isAfter, subDays } from "date-fns";

interface AlertsContextType {
  alerts: Alert[];
  unreadCount: number;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  deleteAlert: (id: string) => void;
  refreshAlerts: () => Promise<void>;
  addAlert: (alert: Alert) => void;
}

const AlertsContext = createContext<AlertsContextType | undefined>(undefined);

/**
 * Generate alerts from real opportunity data
 */
async function generateAlertsFromOpportunities(): Promise<Alert[]> {
  try {
    const opportunities = await fetchOpportunities(100);
    const alerts: Alert[] = [];
    const today = new Date();
    const sevenDaysAgo = subDays(today, 7);
    const thirtyDaysFromNow = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
    
    // Track processed opportunities to avoid duplicates
    const processedIds = new Set<string>();
    
    // Generate alerts for new opportunities (published in last 7 days)
    const newOpportunities = opportunities.filter(opp => {
      const pubDate = new Date(opp.deadlineDate);
      return isAfter(pubDate, sevenDaysAgo) && !processedIds.has(opp.id);
    });
    
    for (const opp of newOpportunities.slice(0, 10)) { // Limit to 10 new opportunity alerts
      processedIds.add(opp.id);
      const pubDate = new Date(opp.deadlineDate);
      alerts.push({
        id: `new-${opp.id}`,
        title: `New ${opp.type}: ${opp.title.substring(0, 60)}${opp.title.length > 60 ? '...' : ''}`,
        description: `${opp.source} published a new ${opp.type.toLowerCase()} opportunity. ${opp.summary.substring(0, 100)}${opp.summary.length > 100 ? '...' : ''}`,
        time: formatDistanceToNow(pubDate, { addSuffix: true }),
        type: "new_opportunity",
        unread: true,
      });
    }
    
    // Generate deadline reminders (deadlines within 30 days)
    const upcomingDeadlines = opportunities.filter(opp => {
      const deadline = opp.deadlineDate;
      const daysUntilDeadline = differenceInDays(deadline, today);
      return isAfter(deadline, today) && daysUntilDeadline <= 30 && daysUntilDeadline > 0 && !processedIds.has(`deadline-${opp.id}`);
    });
    
    for (const opp of upcomingDeadlines.slice(0, 10)) { // Limit to 10 deadline alerts
      processedIds.add(`deadline-${opp.id}`);
      const daysUntilDeadline = differenceInDays(opp.deadlineDate, today);
      alerts.push({
        id: `deadline-${opp.id}`,
        title: `Deadline approaching: ${opp.title.substring(0, 50)}${opp.title.length > 50 ? '...' : ''}`,
        description: `The deadline for this ${opp.type.toLowerCase()} is in ${daysUntilDeadline} day${daysUntilDeadline !== 1 ? 's' : ''}. ${opp.requiredAction}`,
        time: formatDistanceToNow(opp.deadlineDate, { addSuffix: true }),
        type: "deadline",
        unread: true,
      });
    }
    
    // Sort alerts by time (newest first)
    alerts.sort((a, b) => {
      // Parse time strings to sort properly
      const timeA = a.time.includes('ago') ? -1 : 1;
      const timeB = b.time.includes('ago') ? -1 : 1;
      return timeB - timeA;
    });
    
    return alerts;
  } catch (error) {
    console.error('Error generating alerts:', error);
    return [];
  }
}

export function AlertsProvider({ children }: { children: ReactNode }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load alerts from real data when component mounts
  useEffect(() => {
    async function loadAlerts() {
      setIsLoading(true);
      try {
        const generatedAlerts = await generateAlertsFromOpportunities();
        setAlerts(generatedAlerts);
      } catch (error) {
        console.error('Error loading alerts:', error);
      } finally {
        setIsLoading(false);
      }
    }
    loadAlerts();
  }, []);

  const refreshAlerts = async () => {
    setIsLoading(true);
    try {
      const generatedAlerts = await generateAlertsFromOpportunities();
      setAlerts(generatedAlerts);
    } catch (error) {
      console.error('Error refreshing alerts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const unreadCount = alerts.filter((a) => a.unread).length;

  const markAsRead = (id: string) => {
    setAlerts(alerts.map((a) => (a.id === id ? { ...a, unread: false } : a)));
  };

  const markAllAsRead = () => {
    setAlerts(alerts.map((a) => ({ ...a, unread: false })));
  };

  const deleteAlert = (id: string) => {
    setAlerts(alerts.filter((a) => a.id !== id));
  };

  const addAlert = (alert: Alert) => {
    setAlerts((prevAlerts) => [alert, ...prevAlerts]);
  };

  return (
    <AlertsContext.Provider
      value={{ alerts, unreadCount, markAsRead, markAllAsRead, deleteAlert, refreshAlerts, addAlert }}
    >
      {children}
    </AlertsContext.Provider>
  );
}

export function useAlerts() {
  const context = useContext(AlertsContext);
  if (context === undefined) {
    throw new Error("useAlerts must be used within an AlertsProvider");
  }
  return context;
}
