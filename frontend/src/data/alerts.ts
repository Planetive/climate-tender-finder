export interface Alert {
  id: string;
  title: string;
  description: string;
  time: string;
  type: "new_opportunity" | "deadline" | "update" | "source";
  unread: boolean;
}

export const initialAlerts: Alert[] = [
  {
    id: "1",
    title: "New UNDP Climate Finance RFP published",
    description: "A new Request for Proposals for climate finance technical assistance has been published by UNDP Pakistan office.",
    time: "2 hours ago",
    type: "new_opportunity",
    unread: true,
  },
  {
    id: "2",
    title: "Deadline reminder: World Bank Pakistan Energy RFP",
    description: "The deadline for World Bank Pakistan Energy RFP is approaching in 22 days. Consider starting your application soon.",
    time: "5 hours ago",
    type: "deadline",
    unread: true,
  },
  {
    id: "3",
    title: "GCF proposal window opens next week",
    description: "The Green Climate Fund adaptation window will open on January 10th. Prepare your concept notes.",
    time: "1 day ago",
    type: "new_opportunity",
    unread: true,
  },
  {
    id: "4",
    title: "EU Horizon call for climate adaptation",
    description: "New Horizon Europe call announced for innovative climate adaptation solutions with international partnerships.",
    time: "2 days ago",
    type: "new_opportunity",
    unread: false,
  },
  {
    id: "5",
    title: "Source updated: ADB Opportunities Portal",
    description: "The ADB opportunities portal has been refreshed with 5 new listings for South Asia region.",
    time: "3 days ago",
    type: "source",
    unread: false,
  },
  {
    id: "6",
    title: "Application status update: USAID Clean Energy",
    description: "Your expression of interest for USAID Clean Energy program has been acknowledged.",
    time: "4 days ago",
    type: "update",
    unread: false,
  },
];

export const typeLabels = {
  new_opportunity: "New Opportunity",
  deadline: "Deadline",
  update: "Update",
  source: "Source",
};

export const typeStyles = {
  new_opportunity: "bg-primary/10 text-primary border-primary/20",
  deadline: "bg-destructive/10 text-destructive border-destructive/20",
  update: "bg-secondary/10 text-secondary border-secondary/20",
  source: "bg-muted text-muted-foreground border-border",
};
