import { useState, useEffect } from "react";
import { Search, Grid, List, ExternalLink, X } from "lucide-react";
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
import { cacheOpportunitiesById, fetchOpportunities, fetchSources, type Opportunity } from "@/services/api";

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
  News: "bg-muted text-muted-foreground",
};

/** Shared filter dropdown — one style for the whole toolbar */
function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  options: { value: string; label: string }[];
  className?: string;
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className={cn("h-9 w-[10.5rem] bg-card border-border", className)}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export default function Opportunities() {
  const navigate = useNavigate();
  const {
    searchQuery,
    setSearchQuery,
    filters,
    updateFilter,
    clearFilters,
    hasActiveFilters,
  } = useSearch();
  const [viewMode, setViewMode] = useState<"table" | "cards">("table");
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [configuredSourceNames, setConfiguredSourceNames] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadOpportunities() {
      try {
        setLoading(true);
        setError(null);
        const [data, sources] = await Promise.all([
          fetchOpportunities(1000),
          fetchSources(),
        ]);
        setOpportunities(data);
        cacheOpportunitiesById(data);
        setConfiguredSourceNames(sources.map((s) => s.name).sort());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load opportunities");
        console.error("Error loading opportunities:", err);
      } finally {
        setLoading(false);
      }
    }
    loadOpportunities();
  }, []);

  const uniqueOpportunities = opportunities.filter(
    (opp, index, self) => index === self.findIndex((o) => o.id === opp.id)
  );

  const uniqueSources = Array.from(
    new Set([
      ...configuredSourceNames,
      ...uniqueOpportunities.map((opp) => opp.source),
    ])
  ).sort();

  const uniqueCountries = Array.from(
    new Set(uniqueOpportunities.map((opp) => opp.country).filter(Boolean))
  ).sort();

  const uniqueRegions = Array.from(
    new Set(uniqueOpportunities.map((opp) => opp.region).filter(Boolean))
  ).sort();

  const filteredOpportunities = uniqueOpportunities.filter((opp) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      opp.title.toLowerCase().includes(q) ||
      opp.source.toLowerCase().includes(q) ||
      opp.country.toLowerCase().includes(q) ||
      opp.fundingAgency.toLowerCase().includes(q) ||
      opp.tags.some((tag) => tag.toLowerCase().includes(q));

    const matchesType = filters.type === "all" || opp.type === filters.type;
    const matchesKind =
      filters.kind === "all" ||
      opp.contentKind === filters.kind ||
      (filters.kind === "opportunity" && !opp.contentKind);
    const matchesRelevance =
      filters.relevance === "all" || opp.relevance === filters.relevance;
    const matchesCountry = filters.country === "all" || opp.country === filters.country;
    const matchesRegion = filters.region === "all" || opp.region === filters.region;
    const matchesSource = filters.source === "all" || opp.source === filters.source;
    const matchesDateKind =
      filters.dateKind === "all" ||
      opp.dateLabel === filters.dateKind ||
      (filters.dateKind === "Published" &&
        (opp.dateLabel === "Published" || opp.dateLabel === "Posted"));

    return (
      matchesSearch &&
      matchesType &&
      matchesKind &&
      matchesRelevance &&
      matchesCountry &&
      matchesRegion &&
      matchesSource &&
      matchesDateKind
    );
  });

  return (
    <DashboardLayout>
      <div className="space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Opportunities</h1>
          <p className="text-muted-foreground mt-1">
            Browse and filter funding opportunities, grants, and tenders
          </p>
        </div>

        {/* One filter toolbar — no duplicate country / title filters */}
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative w-full sm:w-64 grow sm:grow-0">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search title, source, country…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 h-9 bg-card border-border"
              />
            </div>

            <FilterSelect
              value={filters.kind}
              onChange={(v) => updateFilter("kind", v)}
              placeholder="Category"
              options={[
                { value: "all", label: "All categories" },
                { value: "opportunity", label: "Grants & tenders" },
                { value: "news", label: "News & updates" },
              ]}
            />
            <FilterSelect
              value={filters.source}
              onChange={(v) => updateFilter("source", v)}
              placeholder="Source"
              className="w-[12rem]"
              options={[
                { value: "all", label: "All sources" },
                ...uniqueSources.map((s) => ({ value: s, label: s })),
              ]}
            />
            <FilterSelect
              value={filters.country}
              onChange={(v) => updateFilter("country", v)}
              placeholder="Country"
              options={[
                { value: "all", label: "All countries" },
                ...uniqueCountries.map((c) => ({ value: c, label: c })),
              ]}
            />
            <FilterSelect
              value={filters.region}
              onChange={(v) => updateFilter("region", v)}
              placeholder="Region"
              options={[
                { value: "all", label: "All regions" },
                ...uniqueRegions.map((r) => ({ value: r, label: r })),
              ]}
            />
            <FilterSelect
              value={filters.type}
              onChange={(v) => updateFilter("type", v)}
              placeholder="Type"
              className="w-[8.5rem]"
              options={[
                { value: "all", label: "All types" },
                { value: "Grant", label: "Grant" },
                { value: "RFP", label: "RFP" },
                { value: "Partnership", label: "Partnership" },
                { value: "Tender", label: "Tender" },
                { value: "Accelerator", label: "Accelerator" },
                { value: "Funding", label: "Funding" },
                { value: "News", label: "News" },
              ]}
            />
            <FilterSelect
              value={filters.relevance}
              onChange={(v) => updateFilter("relevance", v)}
              placeholder="Relevance"
              className="w-[8.5rem]"
              options={[
                { value: "all", label: "All relevance" },
                { value: "High", label: "High" },
                { value: "Medium", label: "Medium" },
                { value: "Low", label: "Low" },
              ]}
            />
            <FilterSelect
              value={filters.dateKind}
              onChange={(v) => updateFilter("dateKind", v)}
              placeholder="Date"
              className="w-[10rem]"
              options={[
                { value: "all", label: "All dates" },
                { value: "Deadline", label: "Has deadline" },
                { value: "Published", label: "Published only" },
              ]}
            />

            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="h-9 text-muted-foreground"
              >
                <X className="w-4 h-4 mr-1" />
                Clear
              </Button>
            )}

            <div className="flex gap-1 ml-auto">
              <Button
                variant={viewMode === "table" ? "default" : "outline"}
                size="icon"
                className="h-9 w-9"
                onClick={() => setViewMode("table")}
                aria-label="Table view"
              >
                <List className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === "cards" ? "default" : "outline"}
                size="icon"
                className="h-9 w-9"
                onClick={() => setViewMode("cards")}
                aria-label="Card view"
              >
                <Grid className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        <div className="text-sm text-muted-foreground">
          {loading ? (
            "Loading opportunities..."
          ) : error ? (
            <span className="text-destructive">Error: {error}</span>
          ) : (
            `Showing ${filteredOpportunities.length} of ${uniqueOpportunities.length} opportunities`
          )}
        </div>

        {loading && (
          <div className="text-center py-12 text-muted-foreground">
            Loading opportunities from backend...
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

        {!loading && !error && viewMode === "table" && (
          <div className="bg-card border border-border rounded-lg overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-accent/50">
                  <TableHead className="font-semibold text-foreground">Title</TableHead>
                  <TableHead className="font-semibold text-foreground">Source</TableHead>
                  <TableHead className="font-semibold text-foreground">Country</TableHead>
                  <TableHead className="font-semibold text-foreground">Type</TableHead>
                  <TableHead className="font-semibold text-foreground">Relevance</TableHead>
                  <TableHead className="font-semibold text-foreground">Date</TableHead>
                  <TableHead className="font-semibold text-foreground">Link</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredOpportunities.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-10">
                      No opportunities match these filters.
                      {hasActiveFilters && (
                        <Button variant="link" onClick={clearFilters} className="ml-1">
                          Clear filters
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredOpportunities.map((opp, index) => (
                    <TableRow
                      key={`${opp.id}-${index}`}
                      className={cn(
                        "cursor-pointer hover:bg-accent/50",
                        opp.relevance === "High" && "border-l-4 border-l-primary"
                      )}
                      onClick={() =>
                        navigate(`/opportunities/${opp.id}`, { state: { opportunity: opp } })
                      }
                    >
                      <TableCell className="font-medium text-foreground min-w-[18rem] max-w-xl whitespace-normal break-words leading-snug">
                        {opp.title}
                      </TableCell>
                      <TableCell className="text-muted-foreground whitespace-normal break-words max-w-[14rem]">
                        {opp.source}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{opp.country}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {opp.contentKind === "news" ? (
                            <Badge variant="secondary">News</Badge>
                          ) : (
                            <Badge className={typeStyles[opp.type]}>{opp.type}</Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={relevanceStyles[opp.relevance]}>
                          {opp.relevance}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        <div className="leading-tight">
                          <span>{opp.dateDisplay || opp.deadline}</span>
                          {opp.dateLabel &&
                            opp.dateDisplay &&
                            opp.dateDisplay !== "Not specified" && (
                              <span className="block text-[10px] text-muted-foreground/80">
                                {opp.dateLabel}
                              </span>
                            )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {opp.link ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              window.open(opp.link, "_blank", "noopener,noreferrer");
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
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        )}

        {!loading && !error && viewMode === "cards" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredOpportunities.map((opp, index) => (
              <OpportunityCard
                key={`${opp.id}-${index}`}
                title={opp.title}
                source={opp.source}
                country={opp.country}
                type={opp.type}
                contentKind={opp.contentKind}
                relevance={opp.relevance}
                deadline={opp.dateDisplay || opp.deadline}
                dateLabel={opp.dateLabel}
                link={opp.link}
                onClick={() =>
                  navigate(`/opportunities/${opp.id}`, { state: { opportunity: opp } })
                }
              />
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
