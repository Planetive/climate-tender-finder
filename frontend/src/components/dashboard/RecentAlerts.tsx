import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAlerts } from "@/context/AlertsContext";
import { useNavigate } from "react-router-dom";

export function RecentAlerts() {
  const { alerts, markAsRead } = useAlerts();
  const navigate = useNavigate();
  
  // Show only the latest 4 alerts
  const recentAlerts = alerts.slice(0, 4);

  const handleAlertClick = (id: string) => {
    markAsRead(id);
    navigate("/alerts");
  };

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Bell className="w-5 h-5 text-primary" />
          Recent Alerts
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {recentAlerts.map((alert) => (
          <div
            key={alert.id}
            onClick={() => handleAlertClick(alert.id)}
            className={cn(
              "flex items-start gap-3 p-3 rounded-lg transition-colors cursor-pointer hover:bg-accent",
              alert.unread && "bg-primary/5"
            )}
          >
            <div className={cn(
              "w-2 h-2 rounded-full mt-2 shrink-0",
              alert.unread ? "bg-primary" : "bg-muted"
            )} />
            <div className="flex-1 min-w-0">
              <p className={cn(
                "text-sm line-clamp-1",
                alert.unread ? "font-medium text-foreground" : "text-muted-foreground"
              )}>
                {alert.title}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">{alert.time}</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
