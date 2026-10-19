import { Calendar, MapPin, Building2, ExternalLink } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface OpportunityCardProps {
  title: string;
  source: string;
  country: string;
  type: "Grant" | "RFP" | "Partnership" | "Tender" | "Accelerator" | "Funding" | "News";
  contentKind?: "news" | "opportunity";
  relevance: "High" | "Medium" | "Low";
  deadline: string;
  dateLabel?: string;
  link?: string; // Link to original source
  onClick?: () => void;
}

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
  Accelerator: "bg-primary/70 text-primary-foreground",
  Funding: "bg-secondary/70 text-secondary-foreground",
  News: "bg-muted text-muted-foreground",
};

export function OpportunityCard({
  title,
  source,
  country,
  type,
  contentKind = "opportunity",
  relevance,
  deadline,
  dateLabel = "Date",
  link,
  onClick,
}: OpportunityCardProps) {
  const handleCardClick = (e: React.MouseEvent) => {
    // Don't navigate if clicking on the external link button
    if ((e.target as HTMLElement).closest('.external-link-btn')) {
      return;
    }
    onClick?.();
  };

  const handleExternalLink = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    if (link) {
      window.open(link, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <Card 
      className={cn(
        "bg-card border-border hover:shadow-md transition-shadow cursor-pointer",
        relevance === "High" && "border-l-4 border-l-primary"
      )}
      onClick={handleCardClick}
    >
      <CardContent className="p-5">
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-medium text-foreground flex-1 whitespace-normal break-words leading-snug">
              {title}
            </h3>
            {contentKind === "news" ? (
              <Badge variant="secondary" className="shrink-0">News</Badge>
            ) : (
              <Badge className={cn("shrink-0", typeStyles[type])}>
                {type}
              </Badge>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Building2 className="w-4 h-4" />
              <span>{source}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <MapPin className="w-4 h-4" />
              <span>{country}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              <span>
                {dateLabel !== "Date" ? `${dateLabel}: ` : ""}
                {deadline}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <Badge variant="outline" className={cn("text-xs", relevanceStyles[relevance])}>
              {relevance} Relevance
            </Badge>
            {link && (
              <button
                onClick={handleExternalLink}
                className="external-link-btn text-muted-foreground hover:text-primary transition-colors p-1"
                title="View original source"
              >
                <ExternalLink className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
