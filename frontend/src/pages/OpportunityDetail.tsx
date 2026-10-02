import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { ArrowLeft, Download, Calendar, MapPin, Building2, FileText, Sparkles, Heart, UserPlus, Check, ExternalLink } from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AssigneeSelector, getTeamMembersForExport } from "@/components/assignments/AssigneeSelector";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/context/AuthContext";
import { useAlerts } from "@/context/AlertsContext";
import { cn } from "@/lib/utils";
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

export default function OpportunityDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, isAuthenticated } = useAuth();
  const alertsContext = useAlerts();
  
  const [isInterested, setIsInterested] = useState(false);
  const [assignedOwner, setAssignedOwner] = useState<string | undefined>(undefined);
  const [isAssignDialogOpen, setIsAssignDialogOpen] = useState(false);
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Get team members - defined early so it's always available
  const teamMembers = getTeamMembersForExport();

  // Fetch opportunity from API
  useEffect(() => {
    async function loadOpportunity() {
      if (!id) {
        setError("No opportunity ID provided");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const opportunities = await fetchOpportunities(200);
        const found = opportunities.find((o) => o.id === id);
        
        if (found) {
          setOpportunity(found);
          
          // Load saved assignment
          const assignmentsKey = "funding_tracker_assignments";
          const assignments = JSON.parse(localStorage.getItem(assignmentsKey) || "{}");
          const assignment = assignments[found.id];
          if (assignment) {
            setAssignedOwner(assignment.assignedTo);
          }
        } else {
          setError("Opportunity not found");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load opportunity');
        console.error('Error loading opportunity:', err);
      } finally {
        setLoading(false);
      }
    }
    loadOpportunity();
  }, [id]);

  const handleMarkInterested = () => {
    if (!isAuthenticated) {
      toast({
        variant: "destructive",
        title: "Login required",
        description: "Please sign in to mark opportunities as interested.",
      });
      navigate("/auth");
      return;
    }
    
    setIsInterested(!isInterested);
    toast({
      title: isInterested ? "Removed from interests" : "Marked as interested",
      description: isInterested 
        ? "This opportunity has been removed from your interests."
        : "This opportunity has been added to your interests.",
    });
  };

  const handleAssignOwner = () => {
    if (!isAuthenticated) {
      toast({
        variant: "destructive",
        title: "Login required",
        description: "Please sign in to assign owners.",
      });
      navigate("/auth");
      return;
    }
    setIsAssignDialogOpen(true);
  };

  const handleOwnerSelected = (userId: string) => {
    if (!opportunity || !user) return;
    
    setAssignedOwner(userId);
    const teamMembers = getTeamMembersForExport();
    const member = teamMembers.find((m) => m.id === userId);
    setIsAssignDialogOpen(false);
    
    // Store assignment in localStorage
    const assignmentsKey = "funding_tracker_assignments";
    const assignments = JSON.parse(localStorage.getItem(assignmentsKey) || "{}");
    assignments[opportunity.id] = {
      opportunityId: opportunity.id,
      opportunityTitle: opportunity.title,
      assignedTo: userId,
      assignedBy: user.id,
      assignedByName: user.full_name,
      assignedAt: new Date().toISOString(),
    };
    localStorage.setItem(assignmentsKey, JSON.stringify(assignments));
    
    toast({
      title: "Owner assigned",
      description: `${member?.name} has been assigned as the owner.`,
    });
    
    // Create alert for the assigned person (if not assigning to self)
    if (userId !== user.id && member) {
      alertsContext.addAlert({
        id: `assignment_${opportunity.id}_${Date.now()}`,
        title: `Assigned: ${opportunity.title.substring(0, 50)}${opportunity.title.length > 50 ? '...' : ''}`,
        description: `${user.full_name} assigned you to this ${opportunity.type.toLowerCase()}. Deadline: ${opportunity.deadline}`,
        time: "just now",
        type: "update",
        unread: true,
      });
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const assignedMember = teamMembers.find((m) => m.id === assignedOwner);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
          <p className="text-muted-foreground">Loading opportunity...</p>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !opportunity) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
          <p className="text-muted-foreground">{error || "Opportunity not found"}</p>
          <p className="text-sm text-muted-foreground">
            Make sure the backend server is running on http://localhost:3001
          </p>
          <Button onClick={() => navigate("/opportunities")}>
            Back to Opportunities
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-4xl">
        {/* Back Button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate("/opportunities")}
          className="text-muted-foreground hover:text-foreground -ml-2"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Opportunities
        </Button>

        {/* Header */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className={typeStyles[opportunity.type]}>{opportunity.type}</Badge>
            <Badge variant="outline" className={relevanceStyles[opportunity.relevance]}>
              {opportunity.relevance} Relevance
            </Badge>
            {isInterested && (
              <Badge className="bg-destructive/10 text-destructive border-destructive/20">
                <Heart className="w-3 h-3 mr-1 fill-current" />
                Interested
              </Badge>
            )}
            {assignedMember && (
              <Badge variant="outline" className="bg-primary/10 border-primary/20">
                <Avatar className="w-4 h-4 mr-1">
                  <AvatarFallback className="bg-primary text-primary-foreground text-[8px]">
                    {getInitials(assignedMember.name)}
                  </AvatarFallback>
                </Avatar>
                {assignedMember.name}
              </Badge>
            )}
          </div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">
            {opportunity.title}
          </h1>
          <div className="flex flex-wrap gap-2">
            {opportunity.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="bg-primary/10 text-primary border-0">
                {tag}
              </Badge>
            ))}
          </div>
        </div>

        {/* AI Summary */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              AI Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground leading-relaxed">
              {opportunity.summary}
            </p>
          </CardContent>
        </Card>

        {/* Key Details */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-semibold text-foreground">
              Key Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Funding Agency</p>
                  <p className="text-sm font-medium text-foreground">{opportunity.fundingAgency}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Geography</p>
                  <p className="text-sm font-medium text-foreground">{opportunity.country} ({opportunity.region})</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Deadline</p>
                  <p className="text-sm font-medium text-foreground">{opportunity.deadline}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Required Action</p>
                  <p className="text-sm font-medium text-foreground">{opportunity.requiredAction}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Original Source Link */}
        {opportunity.link && (
          <Card className="bg-card border-border border-primary/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
                <ExternalLink className="w-5 h-5 text-primary" />
                Original Source
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Read the full article or opportunity details on the original website.
              </p>
              <Button
                onClick={() => window.open(opportunity.link, '_blank', 'noopener,noreferrer')}
                className="w-full sm:w-auto bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                View Original Source
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Documents */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-semibold text-foreground">
              Documents
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {opportunity.documents.map((doc, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 rounded-lg bg-accent/50 hover:bg-accent transition-colors"
              >
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-primary" />
                  <span className="text-sm font-medium text-foreground">{doc.name}</span>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="text-primary hover:text-primary"
                  onClick={() => window.open(doc.url, '_blank', 'noopener,noreferrer')}
                >
                  <Download className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <Separator className="bg-border" />
        <div className="flex flex-wrap gap-3">
          <Button 
            onClick={handleMarkInterested}
            className={cn(
              isInterested 
                ? "bg-destructive/10 text-destructive hover:bg-destructive/20 border border-destructive/20" 
                : "bg-primary text-primary-foreground hover:bg-primary/90"
            )}
            variant={isInterested ? "outline" : "default"}
          >
            <Heart className={cn("w-4 h-4 mr-2", isInterested && "fill-current")} />
            {isInterested ? "Interested" : "Mark as Interested"}
          </Button>
          <Button variant="outline" className="border-border" onClick={handleAssignOwner}>
            <UserPlus className="w-4 h-4 mr-2" />
            {assignedMember ? `Owner: ${assignedMember.name}` : "Assign Owner"}
          </Button>
          {opportunity.link && (
            <Button 
              variant="outline" 
              className="border-border"
              onClick={() => window.open(opportunity.link, '_blank', 'noopener,noreferrer')}
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              View Original Source
            </Button>
          )}
        </div>
      </div>

      {/* Assign Owner Dialog */}
      <Dialog open={isAssignDialogOpen} onOpenChange={setIsAssignDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Assign Owner</DialogTitle>
            <DialogDescription>
              Select a team member to be the owner of this opportunity.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <AssigneeSelector
              value={assignedOwner}
              onChange={handleOwnerSelected}
              placeholder="Select an owner..."
            />
          </div>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
}
