import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TeamMemberCard } from "@/components/team/TeamMemberCard";
import { InviteMemberDialog } from "@/components/team/InviteMemberDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UserPlus, Search, Users } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

// Team member type - all are members
interface TeamMember {
  id: string;
  email: string;
  full_name: string;
  role: "member";
  avatar_url?: string;
  joined_at: string;
}

// Storage key for team members
const TEAM_STORAGE_KEY = "funding_tracker_team_members";

// Get team members from localStorage
const getTeamMembers = (): TeamMember[] => {
  try {
    const stored = localStorage.getItem(TEAM_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
    // Initialize with current user if no team exists
    const currentUser = localStorage.getItem("auth_user");
    if (currentUser) {
      const user = JSON.parse(currentUser);
      const initialMember: TeamMember = {
        id: user.id,
        email: user.email,
        full_name: user.full_name,
        role: "member",
        joined_at: new Date().toISOString(),
      };
      saveTeamMembers([initialMember]);
      return [initialMember];
    }
    return [];
  } catch {
    return [];
  }
};

// Save team members to localStorage
const saveTeamMembers = (members: TeamMember[]) => {
  localStorage.setItem(TEAM_STORAGE_KEY, JSON.stringify(members));
};

const Team = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const { user } = useAuth();

  // Load team members on mount
  useEffect(() => {
    const members = getTeamMembers();
    setTeamMembers(members);
  }, []);

  // Add a new team member
  const addTeamMember = (email: string, fullName: string) => {
    const newMember: TeamMember = {
      id: `member_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      email,
      full_name: fullName,
      role: "member",
      joined_at: new Date().toISOString(),
    };
    const updated = [...teamMembers, newMember];
    setTeamMembers(updated);
    saveTeamMembers(updated);
  };

  // Remove a team member
  const removeTeamMember = (id: string) => {
    const updated = teamMembers.filter((m) => m.id !== id);
    setTeamMembers(updated);
    saveTeamMembers(updated);
  };

  const filteredMembers = teamMembers.filter(
    (member) =>
      member.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      member.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Team</h1>
            <p className="text-muted-foreground mt-1">
              Manage your team members and their roles
            </p>
          </div>
          <Button onClick={() => setIsInviteOpen(true)}>
            <UserPlus className="w-4 h-4 mr-2" />
            Add Member
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Users className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{teamMembers.length}</p>
                <p className="text-sm text-muted-foreground">Total Members</p>
              </div>
            </div>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Users className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">
                  {teamMembers.filter((m) => m.id === user?.id).length}
                </p>
                <p className="text-sm text-muted-foreground">Active</p>
              </div>
            </div>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Users className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">
                  {teamMembers.length}
                </p>
                <p className="text-sm text-muted-foreground">Team Size</p>
              </div>
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search team members..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Team Members Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredMembers.map((member) => (
            <TeamMemberCard
              key={member.id}
              member={member}
              currentUserId={user?.id}
              onRemove={removeTeamMember}
            />
          ))}
        </div>

        {filteredMembers.length === 0 && (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground">No members found</h3>
            <p className="text-muted-foreground">
              Try adjusting your search query
            </p>
          </div>
        )}
      </div>

      <InviteMemberDialog 
        open={isInviteOpen} 
        onOpenChange={setIsInviteOpen}
        onAddMember={addTeamMember}
      />
    </DashboardLayout>
  );
};

export default Team;
