import { useState, useEffect } from "react";
import { FileSearch, Sparkles, Clock, Database } from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { OpportunityCard } from "@/components/dashboard/OpportunityCard";
import { RecentAlerts } from "@/components/dashboard/RecentAlerts";
import { UpcomingDeadlines } from "@/components/dashboard/UpcomingDeadlines";
import { useNavigate } from "react-router-dom";
import { differenceInDays, isAfter, subDays } from "date-fns";
import {
  cacheOpportunitiesById,
  fetchOpportunities,
  fetchSources,
  type Opportunity,
} from "@/services/api";

const Index = () => {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        // Load full set so KPI cards are real totals (not capped at 50)
        const [opps, srcs] = await Promise.all([
          fetchOpportunities(1000),
          fetchSources(),
        ]);
        setOpportunities(opps);
        cacheOpportunitiesById(opps);
        setSources(srcs);
      } catch (error) {
        console.error("Error loading dashboard data:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const today = new Date();
  const sevenDaysAgo = subDays(today, 7);

  // Grants/tenders only for opportunity KPIs (news is separate retention)
  const grantTenders = opportunities.filter((o) => o.contentKind !== "news");

  // "New" = published/posted in the last 7 days (NOT deadline — that was the 50 bug)
  const newOpportunities = grantTenders.filter((o) => {
    const pub = o.publishedDate;
    if (!pub || pub.getTime() <= 0) return false;
    return isAfter(pub, sevenDaysAgo) && !isAfter(pub, today);
  }).length;

  const highRelevance = grantTenders.filter((o) => o.relevance === "High").length;

  const upcomingDeadlines = grantTenders.filter(
    (o) =>
      o.dateLabel === "Deadline" &&
      o.deadline !== "Not specified" &&
      isAfter(o.deadlineDate, today) &&
      o.deadlineDate.getFullYear() < 2090 &&
      differenceInDays(o.deadlineDate, today) <= 30
  ).length;

  const activeSources = sources.filter((s) => s.enabled !== false).length;

  // Dashboard list: High relevance first (newest among High), not random "recent"
  const highRelevanceList = [...grantTenders]
    .filter((o) => o.relevance === "High")
    .sort((a, b) => {
      const ta = a.publishedDate?.getTime?.() || a.deadlineDate?.getTime?.() || 0;
      const tb = b.publishedDate?.getTime?.() || b.deadlineDate?.getTime?.() || 0;
      return tb - ta;
    })
    .slice(0, 6);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Track funding opportunities across climate and sustainability sectors
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="New Opportunities"
            value={loading ? "—" : newOpportunities}
            icon={FileSearch}
            trend="Posted in last 7 days"
          />
          <StatCard
            title="High Relevance"
            value={loading ? "—" : highRelevance}
            icon={Sparkles}
            trend="ESG / energy / climate focus"
          />
          <StatCard
            title="Upcoming Deadlines"
            value={loading ? "—" : upcomingDeadlines}
            icon={Clock}
            trend="Next 30 days"
          />
          <StatCard
            title="Active Sources"
            value={loading ? "—" : activeSources}
            icon={Database}
            trend={`${sources.length} configured`}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">
                High Relevance Opportunities
              </h2>
              <button
                onClick={() => navigate("/opportunities")}
                className="text-sm text-primary hover:underline"
              >
                View all
              </button>
            </div>
            {loading ? (
              <div className="text-center py-8 text-muted-foreground">
                Loading opportunities...
              </div>
            ) : highRelevanceList.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No high-relevance opportunities yet. Run a scrape or check Sources.
              </div>
            ) : (
              <div className="grid gap-4">
                {highRelevanceList.map((opportunity) => (
                  <OpportunityCard
                    key={opportunity.id}
                    title={opportunity.title}
                    source={opportunity.source}
                    country={opportunity.country}
                    type={opportunity.type}
                    relevance={opportunity.relevance}
                    deadline={opportunity.dateDisplay || opportunity.deadline}
                    dateLabel={opportunity.dateLabel}
                    contentKind={opportunity.contentKind}
                    link={opportunity.link}
                    onClick={() =>
                      navigate(`/opportunities/${opportunity.id}`, {
                        state: { opportunity },
                      })
                    }
                  />
                ))}
              </div>
            )}
          </div>

          <div className="space-y-6">
            <RecentAlerts />
            <UpcomingDeadlines />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Index;
