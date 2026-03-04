"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { ShieldCheck, Plus, Trash2, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Permission {
  command_name: string;
  guild_id: string;
  role_id: string;
}

export default function PermissionsPage() {
  const { data: session } = useSession();
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const [commandName, setCommandName] = useState("");
  const [guildId, setGuildId] = useState("");
  const [roleId, setRoleId] = useState("");
  const [adding, setAdding] = useState(false);

  const token = (session as { accessToken?: string })?.accessToken;

  const fetchPermissions = () => {
    if (!token) return;
    fetch(`${API_URL}/api/permissions`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setPermissions(Array.isArray(data) ? data : []))
      .catch(() => setPermissions([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPermissions();
  }, [token]);

  const handleAdd = async () => {
    if (!token || !commandName || !guildId || !roleId) return;
    setAdding(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/permissions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ command_name: commandName, guild_id: guildId, role_id: roleId }),
      });
      if (res.ok) {
        setMessage({ text: "Permission added!", ok: true });
        setCommandName("");
        setRoleId("");
        fetchPermissions();
      } else {
        setMessage({ text: "Failed to add permission", ok: false });
      }
    } catch {
      setMessage({ text: "Error adding permission", ok: false });
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (perm: Permission) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/permissions`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(perm),
      });
      if (res.ok) {
        setMessage({ text: "Permission removed!", ok: true });
        fetchPermissions();
      } else {
        setMessage({ text: "Failed to remove permission", ok: false });
      }
    } catch {
      setMessage({ text: "Error removing permission", ok: false });
    }
  };

  // Group permissions by command name
  const grouped = permissions.reduce<Record<string, Permission[]>>((acc, p) => {
    if (!acc[p.command_name]) acc[p.command_name] = [];
    acc[p.command_name].push(p);
    return acc;
  }, {});

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Permissions</h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Restrict commands to specific Discord roles
          </p>
        </div>
      </div>

      {/* Status message */}
      {message && (
        <Card className={message.ok ? "border-green-400 bg-green-50 dark:bg-green-950/20" : "border-red-400 bg-red-50 dark:bg-red-950/20"}>
          <CardContent className="pt-4 flex items-center gap-2">
            {message.ok
              ? <CheckCircle className="h-4 w-4 text-green-500" />
              : <XCircle className="h-4 w-4 text-red-500" />}
            <p className="text-sm">{message.text}</p>
          </CardContent>
        </Card>
      )}

      {/* Add permission form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm sm:text-base flex items-center gap-2">
            <Plus className="h-4 w-4" /> Add Permission Restriction
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Command Name</Label>
              <Input
                placeholder="e.g. review, summarize"
                value={commandName}
                onChange={(e) => setCommandName(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Guild ID</Label>
              <Input
                placeholder="e.g. 1234567890"
                value={guildId}
                onChange={(e) => setGuildId(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Role ID</Label>
              <Input
                placeholder="e.g. 9876543210"
                value={roleId}
                onChange={(e) => setRoleId(e.target.value)}
              />
            </div>
          </div>
          <Button
            onClick={handleAdd}
            disabled={adding || !commandName || !guildId || !roleId}
            size="sm"
          >
            {adding ? "Adding..." : "Add Restriction"}
          </Button>
          <p className="text-xs text-muted-foreground">
            Commands with no restrictions are available to everyone.
            Right-click a role in Discord to copy its ID.
          </p>
        </CardContent>
      </Card>

      {/* Permissions list */}
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading permissions...</p>
      ) : Object.keys(grouped).length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <ShieldCheck className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>No restrictions set.</p>
            <p className="text-xs mt-1">All commands are currently available to everyone.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {Object.entries(grouped).map(([cmd, perms]) => (
            <Card key={cmd}>
              <CardHeader className="pb-2 pt-4 px-4">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <code className="bg-muted px-2 py-0.5 rounded text-xs">/{cmd}</code>
                  <Badge variant="secondary" className="text-xs">
                    {perms.length} role{perms.length !== 1 ? "s" : ""}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-2">
                {perms.map((perm) => (
                  <div
                    key={`${perm.command_name}-${perm.role_id}`}
                    className="flex items-center justify-between rounded-lg border px-3 py-2"
                  >
                    <div className="text-xs text-muted-foreground">
                      <span>Role: <code className="bg-muted px-1 rounded">{perm.role_id}</code></span>
                      <span className="ml-3">Guild: <code className="bg-muted px-1 rounded">{perm.guild_id}</code></span>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                      onClick={() => handleDelete(perm)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
