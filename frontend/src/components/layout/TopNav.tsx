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
  const { searchQuery, setSearchQuery, filters, updateFilter, clearFilters, hasActiveFilters } = useSearch();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);

  // Fetch opportunities to populate filter options
  useEffect(() => {
    async function loadOpportunities() {
      try {
        const data = await fetchOpportunities(200);
        setOpportunities(data);
      } catch (error) {
        console.error('Error loading opportunities for filters:', error);
      }
    }
    loadOpportunities();
  }, []);

  // Get unique values for filter options
  const countries = [...new Set(opportunities.map((o) => o.country))];
  const regions = [...new Set(opportunities.map((o) => o.region))];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    navigate("/opportunities");
  };

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
  };

  return (
    <header className="h-16 border-b border-border bg-card flex items-center justify-between px-4 gap-4">
      <div className="flex items-center gap-4">
        <SidebarTrigger className="text-muted-foreground hover:text-foreground">
          <Menu className="w-5 h-5" />
        </SidebarTrigger>
        <div className="flex items-center gap-3 hidden md:flex">
          <img 
            src="/planetive E logo.PNG" 
            alt="Planetive Logo" 
            className="h-8 w-auto object-contain"
          />
          <h1 className="text-lg font-semibold text-foreground">
            Funding & Tenders Tracker
          </h1>
        </div>
      </div>

      <form onSubmit={handleSearch} className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search by keyword, donor, country..."
            className="pl-10 bg-background border-border"
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </form>

      <Popover>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground relative">
            <SlidersHorizontal className="w-5 h-5" />
            {hasActiveFilters && (
              <Badge className="absolute -top-1 -right-1 w-4 h-4 p-0 flex items-center justify-center text-xs bg-primary text-primary-foreground">
                !
              </Badge>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80" align="end">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-foreground">Filters</h4>
              {hasActiveFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters} className="text-xs">
                  Clear all
                </Button>
              )}
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-sm text-muted-foreground">Type</label>
                <Select value={filters.type} onValueChange={(value) => updateFilter("type", value)}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="All Types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="Grant">Grant</SelectItem>
                    <SelectItem value="RFP">RFP</SelectItem>
                    <SelectItem value="Partnership">Partnership</SelectItem>
                    <SelectItem value="Tender">Tender</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm text-muted-foreground">Relevance</label>
                <Select value={filters.relevance} onValueChange={(value) => updateFilter("relevance", value)}>
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
                <label className="text-sm text-muted-foreground">Country</label>
                <Select value={filters.country} onValueChange={(value) => updateFilter("country", value)}>
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
                <label className="text-sm text-muted-foreground">Region</label>
                <Select value={filters.region} onValueChange={(value) => updateFilter("region", value)}>
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

            <Button className="w-full" onClick={() => navigate("/opportunities")}>
              Apply & View Results
            </Button>
          </div>
        </PopoverContent>
      </Popover>

      <UserMenu />
    </header>
  );
}
