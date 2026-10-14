import { useState, useEffect } from "react";
import { 
  LayoutDashboard, 
  FileSearch, 
  Bell, 
  Database,
  Users,
  RefreshCw,
} from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { triggerFeedRefresh, fetchIngestStatus } from "@/services/api";
import { cn } from "@/lib/utils";

const navItems = [
  { title: "Dashboard", url: "/dashboard", icon: LayoutDashboard },
  { title: "Opportunities", url: "/opportunities", icon: FileSearch },
  { title: "Alerts", url: "/alerts", icon: Bell },
  { title: "Sources", url: "/sources", icon: Database },
  { title: "Team", url: "/team", icon: Users },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();
  const { toast } = useToast();
  const [refreshing, setRefreshing] = useState(false);
  const [ingestHint, setIngestHint] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    async function loadStatus() {
      const status = await fetchIngestStatus();
      if (cancelled || !status?.last_ingest) return;
      const last = status.last_ingest;
      if (last.success === false) {
        setIngestHint(`Last run failed${last.sources_error ? ` (${last.sources_error} source errors)` : ""}`);
      } else if (status.missed_todays_7am_pkt) {
        setIngestHint("Today's 7AM PKT run missed");
      } else if (last.warning) {
        setIngestHint(last.warning);
      } else {
        setIngestHint(
          `Last OK · ${last.upserted ?? last.items ?? 0} saved` +
            (last.sources_error ? ` · ${last.sources_error} errors` : "")
        );
      }
    }
    loadStatus();
    return () => {
      cancelled = true;
    };
  }, [refreshing]);

  async function handleRerun() {
    if (refreshing) return;
    setRefreshing(true);
    toast({
      title: "Refresh started",
      description: "Scraping sources — this can take a few minutes.",
    });
    try {
      const result = await triggerFeedRefresh();
      if (result.running) {
        toast({
          title: "Already running",
          description: "A refresh is already in progress. Wait for it to finish.",
        });
        return;
      }
      if (!result.success) {
        toast({
          title: "Refresh finished with errors",
          description: result.error || `${result.sources_error ?? 0} sources failed`,
          variant: "destructive",
        });
        return;
      }
      toast({
        title: "Refresh complete",
        description: `Saved ${result.upserted ?? result.items ?? 0} items · ${result.sources_ok ?? "?"} ok / ${result.sources_error ?? 0} errors · removed ${result.news_deleted ?? 0} old news.`,
      });
    } catch (err) {
      toast({
        title: "Refresh failed",
        description: err instanceof Error ? err.message : "Could not re-run feeds",
        variant: "destructive",
      });
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <Sidebar collapsible="icon" className="border-r border-border bg-card">
      <SidebarHeader className="p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <img 
            src="/planetive E logo.PNG" 
            alt="Planetive Logo" 
            className="w-8 h-8 object-contain flex-shrink-0"
          />
          {!collapsed && (
            <span className="font-semibold text-foreground text-sm">
              Funding Tracker
            </span>
          )}
        </div>
      </SidebarHeader>
      <SidebarContent className="p-2">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const isActive = location.pathname === item.url;
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild>
                      <NavLink
                        to={item.url}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
                          isActive
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-foreground"
                        )}
                      >
                        <item.icon className="w-5 h-5" />
                        {!collapsed && <span className="text-sm font-medium">{item.title}</span>}
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-2 border-t border-border">
        <Button
          variant="outline"
          size={collapsed ? "icon" : "sm"}
          className="w-full"
          onClick={handleRerun}
          disabled={refreshing}
          title="Re-run scrape now (also runs daily at 7:00 AM Pakistan time)"
        >
          <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin", !collapsed && "mr-2")} />
          {!collapsed && (refreshing ? "Refreshing…" : "Re-run feeds")}
        </Button>
        {!collapsed && (
          <p className="text-[10px] text-muted-foreground px-1 pt-1 leading-snug">
            Auto 7:00 AM PKT (+ catch-up on restart). News 3 days; grants stay.
            {ingestHint ? ` ${ingestHint}.` : ""}
          </p>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
