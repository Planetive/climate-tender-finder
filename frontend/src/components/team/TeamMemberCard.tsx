import { MoreVertical, Shield, User, Trash2 } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/use-toast";
import { format } from "date-fns";

interface TeamMember {
  id: string;
  email: string;
  full_name: string;
  role: "member";
  avatar_url?: string;
  joined_at: string;
}

interface TeamMemberCardProps {
  member: TeamMember;
  currentUserId?: string;
  onRemove?: (id: string) => void;
}

export function TeamMemberCard({ member, currentUserId, onRemove }: TeamMemberCardProps) {
  const { toast } = useToast();
  const isCurrentUser = member.id === currentUserId;

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const handleRemove = () => {
    if (isCurrentUser) {
      toast({
        variant: "destructive",
        title: "Cannot remove yourself",
        description: "You cannot remove yourself from the team.",
      });
      return;
    }
    
    if (onRemove) {
      onRemove(member.id);
      toast({
        title: "Member removed",
        description: `${member.full_name} has been removed from the team.`,
      });
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Avatar className="w-12 h-12">
            <AvatarImage src={member.avatar_url} alt={member.full_name} />
            <AvatarFallback className="bg-primary/10 text-primary font-medium">
              {getInitials(member.full_name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <h3 className="font-medium text-foreground flex items-center gap-2">
              {member.full_name}
              {isCurrentUser && (
                <span className="text-xs text-muted-foreground">(You)</span>
              )}
            </h3>
            <p className="text-sm text-muted-foreground">{member.email}</p>
          </div>
        </div>

        {!isCurrentUser && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={handleRemove}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Remove Member
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <Badge variant="secondary" className="capitalize">
          <User className="w-3 h-3 mr-1" />
          Member
        </Badge>
        <span className="text-xs text-muted-foreground">
          Joined {format(new Date(member.joined_at), "MMM d, yyyy")}
        </span>
      </div>
    </div>
  );
}
