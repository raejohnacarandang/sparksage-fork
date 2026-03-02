"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Shield, Trash2, UserPlus } from "lucide-react";
import { toast } from "sonner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-red-500/10 text-red-500 border-red-500/20",
  moderator: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  viewer: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

const ROLE_PERMISSIONS: Record<string, string[]> = {
  admin: ["Full access to all pages"],
  moderator: ["Overview", "Analytics", "FAQ", "Permissions", "Moderation", "Conversations"],
  viewer: ["Overview", "Analytics (read-only)"],
};

interface DashboardUser {
  discord_id: string;
  username: string;
  avatar: string | null;
  role: string;
  created_at: string;
}

export default function RolesPage() {
  const { data: session } = useSession();
  const [users, setUsers] = useState<DashboardUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [newDiscordId, setNewDiscordId] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newRole, setNewRole] = useState("viewer");

  const token = (session as any)?.accessToken;

  const fetchUsers = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/roles/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      // Handle both array and object responses
      setUsers(Array.isArray(data) ? data : data.users ?? []);
    } catch {
      toast.error("Failed to fetch users");
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const handleAddUser = async () => {
    if (!newDiscordId || !newUsername) {
      toast.error("Discord ID and username are required");
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/roles/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          discord_id: newDiscordId,
          username: newUsername,
          role: newRole,
        }),
      });
      if (res.ok) {
        toast.success(`${newUsername} added as ${newRole}`);
        setNewDiscordId("");
        setNewUsername("");
        setNewRole("viewer");
        fetchUsers();
      }
    } catch {
      toast.error("Failed to add user");
    }
  };

  const handleRoleChange = async (discordId: string, role: string) => {
    try {
      const res = await fetch(`${API_URL}/api/roles/users/${discordId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ discord_id: discordId, role }),
      });
      if (res.ok) {
        toast.success("Role updated");
        fetchUsers();
      }
    } catch {
      toast.error("Failed to update role");
    }
  };

  const handleRemoveUser = async (discordId: string, username: string) => {
    try {
      const res = await fetch(`${API_URL}/api/roles/users/${discordId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        toast.success(`${username} removed`);
        fetchUsers();
      }
    } catch {
      toast.error("Failed to remove user");
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Role Management</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Manage who can access the dashboard and what they can do
        </p>
      </div>

      {/* Role Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(ROLE_PERMISSIONS).map(([role, perms]) => (
          <Card key={role}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Shield className="h-4 w-4" />
                <span className="capitalize">{role}</span>
                <Badge className={`ml-auto text-xs ${ROLE_COLORS[role]}`}>
                  {users.filter((u) => u.role === role).length} users
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="text-xs text-muted-foreground space-y-1">
                {perms.map((p) => (
                  <li key={p} className="flex items-center gap-1">
                    <span className="text-green-500">✓</span> {p}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Add User */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <UserPlus className="h-4 w-4" />
            Add Dashboard User
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              placeholder="Discord ID (e.g. 123456789)"
              value={newDiscordId}
              onChange={(e) => setNewDiscordId(e.target.value)}
              className="flex-1"
            />
            <Input
              placeholder="Username"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              className="flex-1"
            />
            <Select value={newRole} onValueChange={setNewRole}>
              <SelectTrigger className="w-full sm:w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="viewer">Viewer</SelectItem>
                <SelectItem value="moderator">Moderator</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleAddUser} className="whitespace-nowrap">
              Add User
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Get Discord ID: Enable Developer Mode in Discord → Right-click user → Copy User ID
          </p>
        </CardContent>
      </Card>

      {/* Users List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Dashboard Users</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : users.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No users added yet. Add users above to grant dashboard access.
            </p>
          ) : (
            <div className="space-y-2">
              {users.map((user) => (
                <div
                  key={user.discord_id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    {user.avatar ? (
                      <img
                        src={`https://cdn.discordapp.com/avatars/${user.discord_id}/${user.avatar}.png`}
                        alt={user.username}
                        className="h-8 w-8 rounded-full"
                      />
                    ) : (
                      <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-xs font-bold">
                        {user.username[0].toUpperCase()}
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-medium">{user.username}</p>
                      <p className="text-xs text-muted-foreground">{user.discord_id}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Select
                      value={user.role}
                      onValueChange={(role) => handleRoleChange(user.discord_id, role)}
                    >
                      <SelectTrigger className="w-32 h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="viewer">Viewer</SelectItem>
                        <SelectItem value="moderator">Moderator</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                      onClick={() => handleRemoveUser(user.discord_id, user.username)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}