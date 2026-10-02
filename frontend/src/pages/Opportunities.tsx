import { useState, useEffect } from "react";
import { Search, Grid, List, ExternalLink } from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { OpportunityCard } from "@/components/dashboard/OpportunityCard";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useSearch } from "@/context/SearchContext";
import { fetchOpportunities, type Opportunity } from "@/services/api";

const relevanceStyles = {
  High: "bg-primary/10 text-primary border-primary/20",
  Medium: "bg-accent text-accent-foreground border-border",
  Low: "bg-muted/50 text-muted-foreground border-border",
};

const typeStyles = {
  Grant: "bg-primary text-primary-foreground",
  RFP: "bg-secondary text-secondary-foreground",
  Partnership: "bg-primary/80 text-primary-foreground",
  Tender: "bg-secondary/80 text-secondary-foreground",
};

export default function Opportunities() {
  const navigate = useNavigate();
  const { searchQuery, setSearchQuery, filters, updateFilter } = useSearch();
  const [viewMode, setViewMode] = useState<"table" | "cards">("table");
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch opportunities from API when component mounts
  useEffect(() => {
    async function loadOpportunities() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchOpportunities(1000); // Fetch up to 1000 opportunities across all sources
        setOpportunities(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load opportunities');
        console.error('Error loading opportunities:', err);
      } finally {
        setLoading(false);
      }
    }
    loadOpportunities();
  }, []);

  // Deduplicate opportunities by ID to avoid duplicate keys
  const uniqueOpportunities = opportunities.filter((opp, index, self) => 
    index === self.findIndex((o) => o.id === opp.id)
  );

  // Get unique sources for the filter dropdown
  const uniqueSources = Array.from(
    new Set(uniqueOpportunities.map((opp) => opp.source))
  ).sort();

  const filteredOpportunities = uniqueOpportunities.filter((opp) => {
    const matchesSearch =
      opp.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      opp.source.toLowerCase().includes(searchQuery.toLowerCase()) ||
      opp.country.toLowerCase().includes(searchQuery.toLowerCase()) ||
      opp.fundingAgency.toLowerCase().includes(searchQuery.toLowerCase()) ||
      opp.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesType = filters.type === "all" || opp.type === filters.type;
    const matchesRelevance = filters.relevance === "all" || opp.relevance === filters.relevance;
    const matchesCountry = filters.country === "all" || opp.country === filters.country;
    const matchesRegion = filters.region === "all" || opp.region === filters.region;
    const matchesSource = filters.source === "all" || opp.source === filters.source;
    return matchesSearch && matchesType && matchesRelevance && matchesCountry && matchesRegion && matchesSource;
  });

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground">Opportunities</h1>
          <p className="text-muted-foreground mt-1">
            Browse and filter funding opportunities, grants, and tenders
          </p>
        </div>

        {/* Filters Bar */}
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div className="flex flex-1 gap-3 flex-wrap">
            <div className="relative w-full md:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search opportunities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-card border-border"
              />
            </div>
            <Select value={filters.type} onValueChange={(value) => updateFilter("type", value)}>
              <SelectTrigger className="w-40 bg-card border-border">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="Grant">Grant</SelectItem>
                <SelectItem value="RFP">RFP</SelectItem>
                <SelectItem value="Partnership">Partnership</SelectItem>
                <SelectItem value="Tender">Tender</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.relevance} onValueChange={(value) => updateFilter("relevance", value)}>
              <SelectTrigger className="w-40 bg-card border-border">
                <SelectValue placeholder="Relevance" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Relevance</SelectItem>
                <SelectItem value="High">High</SelectItem>
                <SelectItem value="Medium">Medium</SelectItem>
                <SelectItem value="Low">Low</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.source} onValueChange={(value) => updateFilter("source", value)}>
              <SelectTrigger className="w-48 bg-card border-border">
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sources</SelectItem>
                {uniqueSources.map((source) => (
                  <SelectItem key={source} value={source}>
                    {source}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-2">
            <Button
              variant={viewMode === "table" ? "default" : "outline"}
              size="icon"
              onClick={() => setViewMode("table")}
            >
              <List className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === "cards" ? "default" : "outline"}
              size="icon"
              onClick={() => setViewMode("cards")}
            >
              <Grid className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Results Count */}
        <div className="text-sm text-muted-foreground">
          {loading ? (
            "Loading opportunities..."
          ) : error ? (
            <span className="text-destructive">Error: {error}</span>
          ) : (
            `Showing ${filteredOpportunities.length} of ${uniqueOpportunities.length} opportunities`
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12 text-muted-foreground">
            Loading opportunities from backend...
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="text-center py-12">
            <p className="text-destructive mb-4">{error}</p>
            <p className="text-sm text-muted-foreground">
              Make sure the backend server is running on http://localhost:3001
            </p>
          </div>
        )}

        {/* Table View */}
        {!loading && !error && viewMode === "table" && (
          <div className="bg-card border border-border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-accent/50">
                  <TableHead className="font-semibold text-foreground">Title</TableHead>
                  <TableHead className="font-semibold text-foreground">Source</TableHead>
                  <TableHead className="font-semibold text-foreground">Country</TableHead>
                  <TableHead className="font-semibold text-foreground">Type</TableHead>
                  <TableHead className="font-semibold text-foreground">Relevance</TableHead>
                  <TableHead className="font-semibold text-foreground">Deadline</TableHead>
                  <TableHead className="font-semibold text-foreground">Link</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredOpportunities.map((opp, index) => (
                  <TableRow
                    key={`${opp.id}-${index}`}
                    className={cn(
                      "cursor-pointer hover:bg-accent/50",
                      opp.relevance === "High" && "border-l-4 border-l-primary"
                    )}
                    onClick={() => navigate(`/opportunities/${opp.id}`)}
                  >
                    <TableCell className="font-medium text-foreground max-w-xs truncate">
                      {opp.title}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{opp.source}</TableCell>
                    <TableCell className="text-muted-foreground">{opp.country}</TableCell>
                    <TableCell>
                      <Badge className={typeStyles[opp.type]}>{opp.type}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={relevanceStyles[opp.relevance]}>
                        {opp.relevance}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{opp.deadline}</TableCell>
                    <TableCell>
                      {opp.link ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            window.open(opp.link, '_blank', 'noopener,noreferrer');
                          }}
                          className="text-primary hover:text-primary"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </Button>
                      ) : (
                        <span className="text-muted-foreground text-sm">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Cards View */}
        {!loading && !error && viewMode === "cards" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredOpportunities.map((opp, index) => (
              <OpportunityCard
                key={`${opp.id}-${index}`}
                title={opp.title}
                source={opp.source}
                country={opp.country}
                type={opp.type}
                relevance={opp.relevance}
                deadline={opp.deadline}
                link={opp.link}
                onClick={() => navigate(`/opportunities/${opp.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
