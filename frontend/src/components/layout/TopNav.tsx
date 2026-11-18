import { useState, useEffect } from "react";
import { Search, SlidersHorizontal, Menu, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useSearch } from "@/context/SearchContext";
import { useNavigate } from "react-router-dom";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { UserMenu } from "./UserMenu";
import { fetchOpportunities, type Opportunity } from "@/services/api";

export function TopNav() {
  const navigate = useNavigate();
  const {
    searchQuery,
    setSearchQuery,
    filters,
    updateFilter,
    clearFilters,
    hasActiveFilters,
  } = useSearch();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);

  useEffect(() => {
    async function loadOpportunities() {
      try {
        const data = await fetchOpportunities(200);
        setOpportunities(data);
      } catch (error) {
        console.error("Error loading opportunities for filters:", error);
      }
    }
    loadOpportunities();
  }, []);

  const countries = [...new Set(opportunities.map((o) => o.country))];
  const regions = [...new Set(opportunities.map((o) => o.region))];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    navigate("/opportunities");
  };

  return (
    <header className="sticky top-0 z-20 h-16 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="h-full flex items-center gap-3 px-4 md:px-6">
        <SidebarTrigger className="shrink-0 text-muted-foreground hover:text-foreground">
          <Menu className="w-5 h-5" />
        </SidebarTrigger>

        {/* Search + filters as one control group */}
        <form onSubmit={handleSearch} className="flex-1 min-w-0 max-w-2xl">
          <div className="flex items-center gap-0 rounded-lg border border-border bg-background shadow-sm focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-1">
            <div className="relative flex-1 min-w-0">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search opportunities by keyword, source, or country…"
                className="h-10 border-0 bg-transparent pl-10 pr-9 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search opportunities"
              />
              {searchQuery ? (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-sm p-1 text-muted-foreground hover:text-foreground"
                  aria-label="Clear search"
                >
                  <X className="w-4 h-4" />
                </button>
              ) : null}
            </div>

            <div className="h-6 w-px shrink-0 bg-border" />

            <Popover>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  className="h-10 shrink-0 gap-2 rounded-l-none rounded-r-lg px-3 text-muted-foreground hover:text-foreground"
                >
                  <SlidersHorizontal className="w-4 h-4" />
                  <span className="hidden sm:inline text-sm">Filters</span>
                  {hasActiveFilters ? (
                    <Badge className="h-5 min-w-5 px-1.5 text-[10px] bg-primary text-primary-foreground">
                      On
                    </Badge>
                  ) : null}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80" align="end">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-foreground">Filters</h4>
                    {hasActiveFilters ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={clearFilters}
                        className="text-xs"
                      >
                        Clear all
                      </Button>
                    ) : null}
                  </div>

                  <div className="space-y-3">
                    <div className="space-y-1.5">
                      <label className="text-sm text-muted-foreground">Type</label>
                      <Select
                        value={filters.type}
                        onValueChange={(value) => updateFilter("type", value)}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="All Types" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Types</SelectItem>
                          <SelectItem value="Grant">Grant</SelectItem>
                          <SelectItem value="RFP">RFP</SelectItem>
                          <SelectItem value="Partnership">Partnership</SelectItem>
                          <SelectItem value="Tender">Tender</SelectItem>
                          <SelectItem value="Accelerator">Accelerator</SelectItem>
                          <SelectItem value="Funding">Funding</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-sm text-muted-foreground">
                        Relevance
                      </label>
                      <Select
                        value={filters.relevance}
                        onValueChange={(value) => updateFilter("relevance", value)}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="All Relevance" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Relevance</SelectItem>
                          <SelectItem value="High">High</SelectItem>
                          <SelectItem value="Medium">Medium</SelectItem>
                          <SelectItem value="Low">Low</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-sm text-muted-foreground">
                        Country
                      </label>
                      <Select
                        value={filters.country}
                        onValueChange={(value) => updateFilter("country", value)}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="All Countries" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Countries</SelectItem>
                          {countries.map((country) => (
                            <SelectItem key={country} value={country}>
                              {country}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-sm text-muted-foreground">
                        Region
                      </label>
                      <Select
                        value={filters.region}
                        onValueChange={(value) => updateFilter("region", value)}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="All Regions" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Regions</SelectItem>
                          {regions.map((region) => (
                            <SelectItem key={region} value={region}>
                              {region}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <Button
                    className="w-full"
                    onClick={() => navigate("/opportunities")}
                  >
                    Apply & View Results
                  </Button>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </form>

        <div className="ml-auto shrink-0">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
