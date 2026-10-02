import { useState, useEffect } from "react";
import { Database, ExternalLink, RefreshCw, Check, AlertCircle } from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { fetchSources, fetchOpportunitiesBySource } from "@/services/api";

interface Source {
  id: string;
  name: string;
  url: string;
  category: string;
  status: "active" | "paused" | "error";
  lastSync: string;
  opportunitiesFound: number;
  enabled: boolean;
}

// Helper function to categorize sources based on name/URL
function categorizeSource(name: string, url: string): string {
  const lowerName = name.toLowerCase();
  const lowerUrl = url.toLowerCase();
  
  if (lowerName.includes('un') || lowerName.includes('undp') || lowerName.includes('unep')) {
    return "UN Agencies";
  }
  if (lowerName.includes('bank') || lowerUrl.includes('bank')) {
    return "Development Banks";
  }
  if (lowerName.includes('climate') || lowerName.includes('green')) {
    return "Climate Funds";
  }
  if (lowerName.includes('eu') || lowerName.includes('europe')) {
    return "European Union";
  }
  if (lowerName.includes('usaid') || lowerName.includes('uk') || lowerName.includes('fcdo')) {
    return "Bilateral";
  }
  return "Other";
}

const statusConfig = {
  active: { label: "Active", color: "bg-primary text-primary-foreground", icon: Check },
  paused: { label: "Paused", color: "bg-muted text-muted-foreground", icon: AlertCircle },
  error: { label: "Error", color: "bg-destructive text-destructive-foreground", icon: AlertCircle },
};

export default function Sources() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch sources from API when component mounts
  useEffect(() => {
    async function loadSources() {
      try {
        setLoading(true);
        setError(null);
        const backendSources = await fetchSources();
        
        // Transform backend sources to frontend format
        const transformedSources: Source[] = await Promise.all(
          backendSources.map(async (backendSource) => {
            // Fetch opportunities count for this source
            const opportunities = await fetchOpportunitiesBySource(backendSource.id);
            
            return {
              id: backendSource.id,
              name: backendSource.name,
              url: backendSource.url,
              category: categorizeSource(backendSource.name, backendSource.url),
              status: "active" as const, // All sources from backend are active
              lastSync: "Just now", // We can't determine this from backend
              opportunitiesFound: opportunities.length,
              enabled: true,
            };
          })
        );
        
        setSources(transformedSources);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load sources');
        console.error('Error loading sources:', err);
      } finally {
        setLoading(false);
      }
    }
    loadSources();
  }, []);

  const activeCount = sources.filter((s) => s.status === "active").length;
  const totalOpportunities = sources.reduce((acc, s) => acc + s.opportunitiesFound, 0);

  const toggleSource = (id: string) => {
    setSources(sources.map((s) => 
      s.id === id ? { ...s, enabled: !s.enabled, status: s.enabled ? "paused" : "active" } : s
    ));
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Sources</h1>
            <p className="text-muted-foreground mt-1">
              Manage funding opportunity data sources and sync settings
            </p>
          </div>
          <Button 
            className="bg-primary text-primary-foreground hover:bg-primary/90"
            onClick={async () => {
              // Reload sources
              setLoading(true);
              try {
                const backendSources = await fetchSources();
                const transformedSources: Source[] = await Promise.all(
                  backendSources.map(async (backendSource) => {
                    const opportunities = await fetchOpportunitiesBySource(backendSource.id);
                    return {
                      id: backendSource.id,
                      name: backendSource.name,
                      url: backendSource.url,
                      category: categorizeSource(backendSource.name, backendSource.url),
                      status: "active" as const,
                      lastSync: "Just now",
                      opportunitiesFound: opportunities.length,
                      enabled: true,
                    };
                  })
                );
                setSources(transformedSources);
              } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to sync sources');
              } finally {
                setLoading(false);
              }
            }}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Syncing...' : 'Sync All'}
          </Button>
        </div>

        {/* Loading/Error States */}
        {loading && (
          <div className="text-center py-12 text-muted-foreground">
            Loading sources from backend...
          </div>
        )}
        
        {error && !loading && (
          <div className="text-center py-12">
            <p className="text-destructive mb-4">{error}</p>
            <p className="text-sm text-muted-foreground">
              Make sure the backend server is running on http://localhost:3001
            </p>
          </div>
        )}

        {/* Stats */}
        {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-card border-border">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <Database className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{sources.length}</p>
                <p className="text-sm text-muted-foreground">Total Sources</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <Check className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{activeCount}</p>
                <p className="text-sm text-muted-foreground">Active Sources</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <Database className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{totalOpportunities}</p>
                <p className="text-sm text-muted-foreground">Opportunities Found</p>
              </div>
            </CardContent>
          </Card>
        </div>
        )}

        {/* Sources List */}
        {!loading && !error && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-semibold text-foreground">
              Data Sources
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {sources.map((source) => {
                const StatusIcon = statusConfig[source.status].icon;
                return (
                  <div
                    key={source.id}
                    className="flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <Switch
                        checked={source.enabled}
                        onCheckedChange={() => toggleSource(source.id)}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium text-foreground">{source.name}</h3>
                          <Badge 
                            variant="outline" 
                            className={cn("text-xs", statusConfig[source.status].color)}
                          >
                            <StatusIcon className="w-3 h-3 mr-1" />
                            {statusConfig[source.status].label}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                          <span>{source.category}</span>
                          <span>•</span>
                          <span>Last sync: {source.lastSync}</span>
                          <span>•</span>
                          <span>{source.opportunitiesFound} opportunities</span>
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="shrink-0 text-muted-foreground hover:text-foreground"
                      onClick={() => window.open(source.url, "_blank")}
                    >
                      <ExternalLink className="w-4 h-4" />
                    </Button>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
