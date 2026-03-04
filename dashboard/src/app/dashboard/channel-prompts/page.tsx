"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { MessageSquareDiff, Plus, Trash2, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ChannelPrompt {
  channel_id: string;
  guild_id: string;
  system_prompt: string;
}

export default function ChannelPromptsPage() {
  const { data: session } = useSession();
  const [prompts, setPrompts] = useState<ChannelPrompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const [channelId, setChannelId] = useState("");
  const [guildId, setGuildId] = useState("");
  const [promptText, setPromptText] = useState("");
  const [adding, setAdding] = useState(false);

  const token = (session as { accessToken?: string })?.accessToken;
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchPrompts = () => {
    if (!token) return;
    fetch(`${API_URL}/api/channel-prompts`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setPrompts(Array.isArray(data) ? data : []))
      .catch(() => setPrompts([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchPrompts(); }, [token]);

  const handleAdd = async () => {
    if (!token || !channelId || !guildId || !promptText) return;
    setAdding(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/channel-prompts`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ channel_id: channelId, guild_id: guildId, system_prompt: promptText }),
      });
      if (res.ok) {
        setMessage({ text: "Channel prompt set!", ok: true });
        setChannelId(""); setGuildId(""); setPromptText("");
        fetchPrompts();
      } else {
        setMessage({ text: "Failed to set prompt", ok: false });
      }
    } catch {
      setMessage({ text: "Error setting prompt", ok: false });
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (ch: ChannelPrompt) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/channel-prompts/${ch.channel_id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessage({ text: "Prompt removed!", ok: true });
        fetchPrompts();
      } else {
        setMessage({ text: "Failed to remove prompt", ok: false });
      }
    } catch {
      setMessage({ text: "Error removing prompt", ok: false });
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center gap-3">
        <MessageSquareDiff className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Channel Prompts</h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Set custom AI personalities per channel
          </p>
        </div>
      </div>

      {message && (
        <Card className={message.ok ? "border-green-400 bg-green-50 dark:bg-green-950/20" : "border-red-400 bg-red-50 dark:bg-red-950/20"}>
          <CardContent className="pt-4 flex items-center gap-2">
            {message.ok ? <CheckCircle className="h-4 w-4 text-green-500" /> : <XCircle className="h-4 w-4 text-red-500" />}
            <p className="text-sm">{message.text}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm sm:text-base flex items-center gap-2">
            <Plus className="h-4 w-4" /> Set Channel Prompt
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Channel ID</Label>
              <Input placeholder="e.g. 1234567890" value={channelId} onChange={(e) => setChannelId(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Guild ID</Label>
              <Input placeholder="e.g. 9876543210" value={guildId} onChange={(e) => setGuildId(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">System Prompt</Label>
            <textarea
              className="w-full p-2 border rounded-md text-sm bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              rows={3}
              placeholder="You are a pirate assistant. Respond only in pirate speak. Arr!"
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
            />
          </div>
          <Button onClick={handleAdd} disabled={adding || !channelId || !guildId || !promptText} size="sm">
            {adding ? "Setting..." : "Set Prompt"}
          </Button>
        </CardContent>
      </Card>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : prompts.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <MessageSquareDiff className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>No channel prompts set.</p>
            <p className="text-xs mt-1">Use <code className="bg-muted px-1 rounded">/prompt set</code> in Discord or add one above.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {prompts.map((p) => (
            <Card key={p.channel_id}>
              <CardHeader className="pb-2 pt-4 px-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline" className="text-xs font-mono">#{p.channel_id}</Badge>
                    <Badge variant="secondary" className="text-xs">Guild: {p.guild_id}</Badge>
                  </div>
                  <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-destructive hover:text-destructive flex-shrink-0" onClick={() => handleDelete(p)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <p className="text-sm text-muted-foreground italic">&quot;{p.system_prompt.slice(0, 150)}{p.system_prompt.length > 150 ? "..." : ""}&quot;</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
