"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Puzzle, CheckCircle, XCircle, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Plugin {
  name: string;
  version: string;
  author: string;
  description: string;
  cog: string;
  enabled: boolean;
}

export default function PluginsPage() {
  const { data: session } = useSession();
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const token = (session as { accessToken?: string })?.accessToken;

  const fetchPlugins = () => {
    if (!token) return;
    fetch(`${API_URL}/api/plugins`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setPlugins(Array.isArray(data) ? data : []))
      .catch(() => setPlugins([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPlugins();
  }, [token]);

  const handleToggle = async (plugin: Plugin) => {
    if (!token) return;
    setActionLoading(plugin.name);
    setMessage(null);

    const action = plugin.enabled ? "disable" : "enable";
    try {
      const res = await fetch(`${API_URL}/api/plugins/${plugin.name}/${action}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setMessage({ text: data.message || `Plugin ${action}d`, ok: res.ok });
      fetchPlugins();
    } catch {
      setMessage({ text: "Action failed", ok: false });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center gap-3">
        <Puzzle className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Plugins</h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Manage community extension plugins
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

      {/* How to add plugins */}
      <Card className="border-dashed">
        <CardContent className="pt-4 flex items-start gap-2">
          <Info className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            To add a plugin, create a folder in <code className="bg-muted px-1 rounded">plugins/</code> with a{" "}
            <code className="bg-muted px-1 rounded">manifest.json</code> and cog file. Plugins can be
            enabled/disabled without restarting the bot.
          </p>
        </CardContent>
      </Card>

      {/* Plugin list */}
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading plugins...</p>
      ) : plugins.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <Puzzle className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>No plugins found.</p>
            <p className="text-xs mt-1">
              Add plugin folders to the <code className="bg-muted px-1 rounded">plugins/</code> directory.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {plugins.map((plugin) => (
            <Card key={plugin.name} className="hover:bg-muted/30 transition-colors">
              <CardHeader className="pb-2 pt-4 px-4">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CardTitle className="text-sm font-medium">{plugin.name}</CardTitle>
                    <Badge variant="outline" className="text-xs">v{plugin.version}</Badge>
                    <Badge
                      variant={plugin.enabled ? "default" : "secondary"}
                      className="text-xs"
                    >
                      {plugin.enabled ? "✅ Enabled" : "⭕ Disabled"}
                    </Badge>
                  </div>
                  <Button
                    size="sm"
                    variant={plugin.enabled ? "destructive" : "default"}
                    disabled={actionLoading === plugin.name}
                    onClick={() => handleToggle(plugin)}
                    className="text-xs h-7"
                  >
                    {actionLoading === plugin.name
                      ? "..."
                      : plugin.enabled ? "Disable" : "Enable"}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <p className="text-sm text-muted-foreground">{plugin.description}</p>
                <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                  <span>by <strong>{plugin.author}</strong></span>
                  <span>cog: <code className="bg-muted px-1 rounded">{plugin.cog}</code></span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
