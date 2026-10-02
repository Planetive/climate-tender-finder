import { useState, useEffect } from "react";
import { FileSearch, Sparkles, Clock, Database } from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/dashboard/StatCard";
import { OpportunityCard } from "@/components/dashboard/OpportunityCard";
import { RecentAlerts } from "@/components/dashboard/RecentAlerts";
import { UpcomingDeadlines } from "@/components/dashboard/UpcomingDeadlines";
import { useNavigate } from "react-router-dom";
import { differenceInDays, isAfter, subDays } from "date-fns";
import { fetchOpportunities, fetchSources, type Opportunity } from "@/services/api";

const Index = () => {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Fetch data from API when component mounts
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [opps, srcs] = await Promise.all([
          fetchOpportunities(50),
          fetchSources()
        ]);
        setOpportunities(opps);
        setSources(srcs);
      } catch (error) {
        console.error('Error loading dashboard data:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);
  
  const today = new Date();
  const sevenDaysAgo = subDays(today, 7);
  
  // Dynamic stats calculations
  const newOpportunities = opportunities.filter(
    (o) => isAfter(o.deadlineDate, sevenDaysAgo)
  ).length;
  
  const highRelevance = opportunities.filter((o) => o.relevance === "High").length;
  
  const upcomingDeadlines = opportunities.filter(
    (o) => isAfter(o.deadlineDate, today) && differenceInDays(o.deadlineDate, today) <= 30
  ).length;
  
  const recentOpportunities = opportunities.slice(0, 4);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Track funding opportunities across climate and sustainability sectors
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="New Opportunities"
            value={newOpportunities}
            icon={FileSearch}
            trend="Last 7 days"
          />
          <StatCard
            title="High Relevance"
            value={highRelevance}
            icon={Sparkles}
            trend="Total available"
          />
          <StatCard
            title="Upcoming Deadlines"
            value={upcomingDeadlines}
            icon={Clock}
            trend="Next 30 days"
          />
          <StatCard
            title="Active Sources"
            value={loading ? 0 : sources.length}
            icon={Database}
            trend="Monitoring today"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Opportunities Section */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">
                Recent Opportunities
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
            ) : recentOpportunities.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No opportunities found. Make sure the backend is running.
              </div>
            ) : (
            <div className="grid gap-4">
              {recentOpportunities.map((opportunity) => (
                <OpportunityCard
                  key={opportunity.id}
                  title={opportunity.title}
                  source={opportunity.source}
                  country={opportunity.country}
                  type={opportunity.type}
                  relevance={opportunity.relevance}
                  deadline={opportunity.deadline}
                  link={opportunity.link}
                  onClick={() => navigate(`/opportunities/${opportunity.id}`)}
                />
              ))}
            </div>
            )}
          </div>

          {/* Sidebar Widgets */}
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
