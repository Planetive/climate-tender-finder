import React, { createContext, useContext, useState, ReactNode } from "react";

interface SearchFilters {
  type: string;
  kind: string;
  relevance: string;
  country: string;
  region: string;
  source: string;
  /** all | Deadline | Published | Posted */
  dateKind: string;
}

interface SearchContextType {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  filters: SearchFilters;
  setFilters: (filters: SearchFilters) => void;
  updateFilter: (key: keyof SearchFilters, value: string) => void;
  clearFilters: () => void;
  hasActiveFilters: boolean;
}

const defaultFilters: SearchFilters = {
  type: "all",
  kind: "all",
  relevance: "all",
  country: "all",
  region: "all",
  source: "all",
  dateKind: "all",
};

const SearchContext = createContext<SearchContextType | undefined>(undefined);

export function SearchProvider({ children }: { children: ReactNode }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters);

  const updateFilter = (key: keyof SearchFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters(defaultFilters);
    setSearchQuery("");
  };

  const hasActiveFilters =
    searchQuery !== "" ||
    filters.type !== "all" ||
    filters.kind !== "all" ||
    filters.relevance !== "all" ||
    filters.country !== "all" ||
    filters.region !== "all" ||
    filters.source !== "all" ||
    filters.dateKind !== "all";

  return (
    <SearchContext.Provider
      value={{
        searchQuery,
        setSearchQuery,
        filters,
        setFilters,
        updateFilter,
        clearFilters,
        hasActiveFilters,
      }}
    >
      {children}
    </SearchContext.Provider>
  );
}

export function useSearch() {
  const context = useContext(SearchContext);
  if (context === undefined) {
    throw new Error("useSearch must be used within a SearchProvider");
  }
  return context;
}
