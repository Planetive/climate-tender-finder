import { useState, useEffect } from "react";
import { Database, ExternalLink, RefreshCw, Check, AlertCircle } from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  fetchSources,
  toggleSourceEnabled,
  scrapeOneSource,
  fetchIngestStatus,
  triggerFeedRefresh,
  type IngestStatusResponse,
} from "@/services/api";

interface Source {
  id: string;
  name: string;
  url: string;
  category: string;
  contentKind: string;
  status: "active" | "paused" | "error";
  lastSync: string;
  opportunitiesFound: number;
  enabled: boolean;
  healthStatus?: string | null;
  lastError?: string | null;
  healthMessage?: string | null;
}

const statusConfig = {
  active: { label: "On", color: "bg-primary text-primary-foreground", icon: Check },
  paused: { label: "Off", color: "bg-muted text-muted-foreground", icon: AlertCircle },
  error: { label: "Error", color: "bg-destructive text-destructive-foreground", icon: AlertCircle },
};

function formatLastSync(iso: string | null | undefined): string {
  if (!iso) return "Not run yet";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function Sources() {
  const { toast } = useToast();
  const [sources, setSources] = useState<Source[]>([]);
  const [ingest, setIngest] = useState<IngestStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  /** Source id currently being scraped after turn-on */
  const [scrapingSourceId, setScrapingSourceId] = useState<string | null>(null);
  const [scrapingSourceName, setScrapingSourceName] = useState<string | null>(null);
  const [scraping, setScraping] = useState(false);

  async function handleRunScrape() {
    if (scraping) return;
    setScraping(true);
    toast({
      title: "Scrape started",
      description: "Running enabled sources — this can take a few minutes.",
    });
    try {
      const result = await triggerFeedRefresh();
      if (result.running) {
        toast({
          title: "Already running",
          description: "A scrape is already in progress. Wait for it to finish.",
        });
        return;
      }
      if (!result.success) {
        toast({
          title: "Scrape finished with errors",
          description: result.error || `${result.sources_error ?? 0} sources failed`,
          variant: "destructive",
        });
      } else {
        toast({
          title: "Scrape complete",
          description: `Saved ${result.upserted ?? result.items ?? 0} items · ${result.sources_ok ?? "?"} ok / ${result.sources_error ?? 0} errors.`,
        });
      }
      await loadSources();
    } catch (err) {
      toast({
        title: "Scrape failed",
        description: err instanceof Error ? err.message : "Could not start scrape",
        variant: "destructive",
      });
    } finally {
      setScraping(false);
    }
  }

  async function loadSources(opts?: { silent?: boolean }) {
    const silent = Boolean(opts?.silent);
    try {
      if (!silent) {
        setLoading(true);
        setError(null);
      }
      const [backendSources, status] = await Promise.all([
        fetchSources(),
        fetchIngestStatus(),
      ]);
      setIngest(status);
      const transformed: Source[] = backendSources.map((s) => ({
        id: s.id,
        name: s.name,
        url: s.url,
        category: s.category || "Other",
        contentKind: s.content_kind || "opportunity",
        status: (s.status as Source["status"]) || (s.enabled === false ? "paused" : "active"),
        lastSync: formatLastSync(s.last_sync),
        opportunitiesFound: s.opportunities_found ?? 0,
        enabled: s.enabled !== false,
        healthStatus: s.health?.status,
        lastError: s.health?.last_error,
        healthMessage: s.health?.message,
      }));
      setSources(transformed);
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : "Failed to load sources");
      }
      console.error("Error loading sources:", err);
    } finally {
      if (!silent) setLoading(false);
    }
  }

  useEffect(() => {
    loadSources();
  }, []);

  const activeCount = sources.filter((s) => s.enabled).length;
  const errorCount = sources.filter((s) => s.status === "error").length;
  const totalOpportunities = sources.reduce((acc, s) => acc + s.opportunitiesFound, 0);
  const last = ingest?.last_ingest;

  async function toggleSource(id: string, nextEnabled: boolean) {
    const sourceName = sources.find((s) => s.id === id)?.name || id;
    setTogglingId(id);
    setSources((prev) =>
      prev.map((s) =>
        s.id === id
          ? {
              ...s,
              enabled: nextEnabled,
              status: nextEnabled
                ? s.healthStatus === "error"
                  ? "error"
                  : "active"
                : "paused",
            }
          : s
      )
    );

    // 1) Save on/off first
    try {
      await toggleSourceEnabled(id, nextEnabled);
    } catch (err) {
      setSources((prev) =>
        prev.map((s) =>
          s.id === id
            ? { ...s, enabled: !nextEnabled, status: !nextEnabled ? "active" : "paused" }
            : s
        )
      );
      toast({
        title: "Could not update source",
        description: err instanceof Error ? err.message : "Try again",
        variant: "destructive",
      });
      setTogglingId(null);
      return;
    }

    setTogglingId(null);

    // Turning OFF — done
    if (!nextEnabled) {
      toast({
        title: "Source disabled",
        description: "It will be skipped on Run scrape now and the 7:00 AM PKT job.",
      });
      return;
    }

    // 2) Turning ON — scrape this source now (keep switch ON even if scrape fails)
    setScrapingSourceId(id);
    setScrapingSourceName(sourceName);
    toast({
      title: `Scraping ${sourceName}`,
      description: "Fetching this source now — hang on, this can take a minute…",
    });

    try {
      const result = await scrapeOneSource(id);

      if (result.running) {
        toast({
          title: "Another scrape is running",
          description: "Source is on. Wait for the current job to finish, then use Run scrape now.",
        });
      } else if (!result.success) {
        toast({
          title: `${sourceName} scrape failed`,
          description: result.error || "Could not fetch this source",
          variant: "destructive",
        });
      } else {
        const kept = result.items ?? 0;
        const saved = result.upserted ?? kept;
        toast({
          title: `${sourceName} ready`,
          description: `Got ${kept} relevant item${kept === 1 ? "" : "s"} · saved ${saved} to the database.`,
        });
      }
      await loadSources({ silent: true });
    } catch (err) {
      toast({
        title: `${sourceName} scrape failed`,
        description: err instanceof Error ? err.message : "Try again or use Run scrape now",
        variant: "destructive",
      });
      await loadSources({ silent: true });
    } finally {
      setScrapingSourceId(null);
      setScrapingSourceName(null);
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Sources</h1>
            <p className="text-muted-foreground mt-1">
              Turn a source on to scrape it now. Off sources are skipped at 7:00 AM PKT and Run scrape now.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={loadSources}
              disabled={loading || scraping || !!scrapingSourceId}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              {loading ? "Loading…" : "Refresh list"}
            </Button>
            <Button
              className="bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={handleRunScrape}
              disabled={scraping || loading || !!scrapingSourceId}
              title="Manually run scrape (same job as 7:00 AM PKT)"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${scraping ? "animate-spin" : ""}`} />
              {scraping ? "Scraping…" : "Run scrape now"}
            </Button>
          </div>
        </div>

        {/* Live banner while a single source is scraping after turn-on */}
        {scrapingSourceId && (
          <Card className="border-primary/40 bg-primary/5">
            <CardContent className="p-4 flex items-center gap-3 text-sm">
              <RefreshCw className="w-5 h-5 text-primary animate-spin shrink-0" />
              <div>
                <p className="font-medium text-foreground">
                  Scraping {scrapingSourceName || scrapingSourceId}…
                </p>
                <p className="text-muted-foreground">
                  Fetching and saving items for this source. Results appear when it finishes.
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Ingest health banner */}
        {!loading && last && (
          <Card className={cn(
            "border",
            last.success === false ? "border-destructive/40 bg-destructive/5" : "border-border bg-card"
          )}>
            <CardContent className="p-4 text-sm space-y-1">
              <p className="font-medium text-foreground">
                Last ingest: {last.success === false ? "Failed" : "OK"}
                {last.trigger ? ` (${last.trigger})` : ""}
              </p>
              <p className="text-muted-foreground">
                {last.finished_at ? formatLastSync(last.finished_at) : "—"}
                {" · "}
                {last.upserted ?? last.items ?? 0} saved
                {" · "}
                {last.sources_ok ?? "—"} ok / {last.sources_error ?? 0} errors
                {typeof ingest?.seconds_until_next_7am_pkt === "number" && (
                  <> · next 7:00 PKT in ~{Math.round((ingest.seconds_until_next_7am_pkt || 0) / 3600)}h</>
                )}
              </p>
              {last.error && <p className="text-destructive">{last.error}</p>}
              {last.warning && <p className="text-amber-700 dark:text-amber-400">{last.warning}</p>}
              {ingest?.missed_todays_7am_pkt && (
                <p className="text-amber-700 dark:text-amber-400">
                  Today&apos;s 7:00 AM PKT run looks missed — use Re-run feeds or wait for catch-up on restart.
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {loading && (
          <div className="text-center py-12 text-muted-foreground">
            Loading sources…
          </div>
        )}

        {error && !loading && (
          <div className="text-center py-12">
            <p className="text-destructive mb-4">{error}</p>
            <p className="text-sm text-muted-foreground">
              Make sure the backend is running, then try Refresh list.
            </p>
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
                  <p className="text-sm text-muted-foreground">Enabled</p>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-card border-border">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-destructive/10 flex items-center justify-center">
                  <AlertCircle className="w-6 h-6 text-destructive" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{errorCount}</p>
                  <p className="text-sm text-muted-foreground">Last-run errors</p>
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
                  <p className="text-sm text-muted-foreground">Items in database</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

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
                  const isScrapingThis = scrapingSourceId === source.id;
                  return (
                    <div
                      key={source.id}
                      className={cn(
                        "flex items-center justify-between p-4 hover:bg-accent/50 transition-colors",
                        isScrapingThis && "bg-primary/5"
                      )}
                    >
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        <Switch
                          checked={source.enabled}
                          disabled={
                            togglingId === source.id ||
                            !!scrapingSourceId ||
                            scraping
                          }
                          onCheckedChange={(checked) => toggleSource(source.id, checked)}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-medium text-foreground">{source.name}</h3>
                            {isScrapingThis ? (
                              <Badge variant="outline" className="text-xs border-primary text-primary">
                                <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                                Scraping…
                              </Badge>
                            ) : (
                              <Badge
                                variant="outline"
                                className={cn("text-xs", statusConfig[source.status].color)}
                              >
                                <StatusIcon className="w-3 h-3 mr-1" />
                                {statusConfig[source.status].label}
                              </Badge>
                            )}
                            <Badge variant="secondary" className="text-xs">
                              {source.contentKind === "news" ? "News" : "Opportunity"}
                            </Badge>
                            {source.healthStatus === "empty" && source.enabled && !isScrapingThis && (
                              <Badge variant="outline" className="text-xs">0 items</Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground flex-wrap">
                            <span>{source.category}</span>
                            <span>•</span>
                            <span>
                              {isScrapingThis
                                ? "Fetching now…"
                                : `Last run: ${source.lastSync}`}
                            </span>
                            <span>•</span>
                            <span>{source.opportunitiesFound} stored</span>
                          </div>
                          {source.lastError && !isScrapingThis && (
                            <p className="text-xs text-destructive mt-1 truncate" title={source.lastError}>
                              Error: {source.lastError}
                            </p>
                          )}
                          {!source.lastError && source.healthMessage && source.healthStatus === "empty" && !isScrapingThis && (
                            <p className="text-xs text-muted-foreground mt-1">{source.healthMessage}</p>
                          )}
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
