import { useState, useEffect } from "react";
import { Check, UserPlus } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Get team members from localStorage
const getTeamMembers = () => {
  try {
    const stored = localStorage.getItem("funding_tracker_team_members");
    if (stored) {
      const members = JSON.parse(stored);
      return members.map((m: any) => ({
        id: m.id,
        name: m.full_name,
        email: m.email,
      }));
    }
  } catch {
    return [];
  }
  return [];
};

interface AssigneeSelectorProps {
  value?: string;
  onChange: (userId: string) => void;
  placeholder?: string;
}

export function AssigneeSelector({ value, onChange, placeholder = "Select assignee" }: AssigneeSelectorProps) {
  const [teamMembers, setTeamMembers] = useState(getTeamMembers());

  // Update team members when localStorage changes
  useEffect(() => {
    const updateMembers = () => {
      setTeamMembers(getTeamMembers());
    };
    
    // Check for changes periodically and on storage events
    const interval = setInterval(updateMembers, 1000);
    window.addEventListener('storage', updateMembers);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('storage', updateMembers);
    };
  }, []);

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const selectedMember = teamMembers.find((m) => m.id === value);

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder={placeholder}>
          {selectedMember && (
            <div className="flex items-center gap-2">
              <Avatar className="w-5 h-5">
                <AvatarFallback className="bg-primary/10 text-primary text-xs">
                  {getInitials(selectedMember.name)}
                </AvatarFallback>
              </Avatar>
              <span>{selectedMember.name}</span>
            </div>
          )}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {teamMembers.map((member) => (
          <SelectItem key={member.id} value={member.id}>
            <div className="flex items-center gap-2">
              <Avatar className="w-5 h-5">
                <AvatarFallback className="bg-primary/10 text-primary text-xs">
                  {getInitials(member.name)}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col">
                <span>{member.name}</span>
                <span className="text-xs text-muted-foreground">{member.email}</span>
              </div>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

// Export function to get team members (for use elsewhere)
export const getTeamMembersForExport = getTeamMembers;
