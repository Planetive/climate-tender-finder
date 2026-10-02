import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CalendarDays } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { differenceInDays, format, isAfter } from "date-fns";
import { fetchOpportunities, type Opportunity } from "@/services/api";

export function UpcomingDeadlines() {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const today = new Date();

  // Fetch opportunities from API
  useEffect(() => {
    async function loadOpportunities() {
      try {
        const data = await fetchOpportunities(50);
        setOpportunities(data);
      } catch (error) {
        console.error('Error loading opportunities for deadlines:', error);
      } finally {
        setLoading(false);
      }
    }
    loadOpportunities();
  }, []);

  // Filter opportunities with future deadlines and calculate days left
  const upcomingDeadlines = opportunities
    .filter((opp) => isAfter(opp.deadlineDate, today))
    .map((opp) => ({
      id: opp.id,
      title: opp.title,
      date: format(opp.deadlineDate, "MMM d, yyyy"),
      daysLeft: differenceInDays(opp.deadlineDate, today),
    }))
    .sort((a, b) => a.daysLeft - b.daysLeft)
    .slice(0, 4);

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
          <CalendarDays className="w-5 h-5 text-primary" />
          Upcoming Deadlines
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading ? (
          <p className="text-sm text-muted-foreground text-center py-4">Loading deadlines...</p>
        ) : upcomingDeadlines.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">No upcoming deadlines</p>
        ) : (
        <>
        {upcomingDeadlines.map((deadline) => (
          <div
            key={deadline.id}
            onClick={() => navigate(`/opportunities/${deadline.id}`)}
            className="flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors cursor-pointer"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground line-clamp-1">
                {deadline.title}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">{deadline.date}</p>
            </div>
            <Badge 
              variant="outline" 
              className={cn(
                "shrink-0 ml-3",
                deadline.daysLeft <= 14 
                  ? "border-primary text-primary bg-primary/10" 
                  : "border-border text-muted-foreground"
              )}
            >
              {deadline.daysLeft}d left
            </Badge>
          </div>
        ))}
        </>
        )}
      </CardContent>
    </Card>
  );
}
