"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Cpu, Plus, Trash2, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ChannelProvider {
  channel_id: string;
  provider: string;
}

const PROVIDER_NAMES: Record<string, string> = {
  gemini: "Google Gemini",
  groq: "Groq",
  openrouter: "OpenRouter",
  anthropic: "Anthropic Claude",
  openai: "OpenAI",
};

export default function ChannelProvidersPage() {
  const { data: session } = useSession();
  const [overrides, setOverrides] = useState<ChannelProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const [channelId, setChannelId] = useState("");
  const [provider, setProvider] = useState("gemini");
  const [adding, setAdding] = useState(false);

  const token = (session as { accessToken?: string })?.accessToken;
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchOverrides = () => {
    if (!token) return;
    fetch(`${API_URL}/api/channel-providers`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setOverrides(Array.isArray(data) ? data : []))
      .catch(() => setOverrides([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchOverrides(); }, [token]);

  const handleAdd = async () => {
    if (!token || !channelId || !provider) return;
    setAdding(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/channel-providers`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ channel_id: channelId, provider }),
      });
      if (res.ok) {
        setMessage({ text: "Channel provider set!", ok: true });
        setChannelId("");
        fetchOverrides();
      } else {
        setMessage({ text: "Failed to set provider", ok: false });
      }
    } catch {
      setMessage({ text: "Error setting provider", ok: false });
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (ch: ChannelProvider) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/channel-providers/${ch.channel_id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessage({ text: "Override removed!", ok: true });
        fetchOverrides();
      } else {
        setMessage({ text: "Failed to remove override", ok: false });
      }
    } catch {
      setMessage({ text: "Error removing override", ok: false });
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center gap-3">
        <Cpu className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Channel Providers</h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Override the AI provider for specific channels
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
            <Plus className="h-4 w-4" /> Set Channel Provider Override
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Channel ID</Label>
              <Input placeholder="e.g. 1234567890" value={channelId} onChange={(e) => setChannelId(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Provider</Label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(PROVIDER_NAMES).map(([key, name]) => (
                  <button
                    key={key}
                    onClick={() => setProvider(key)}
                    className={`px-3 py-1.5 rounded-lg text-xs border transition-colors
                      ${provider === key
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-background border-border hover:bg-muted"
                      }`}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <Button onClick={handleAdd} disabled={adding || !channelId} size="sm">
            {adding ? "Setting..." : "Set Override"}
          </Button>
          <p className="text-xs text-muted-foreground">
            Channels without an override use the global primary provider.
          </p>
        </CardContent>
      </Card>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : overrides.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground">
            <Cpu className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p>No channel overrides set.</p>
            <p className="text-xs mt-1">All channels use the global provider from Settings.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {overrides.map((o) => (
            <Card key={o.channel_id}>
              <CardHeader className="pb-2 pt-4 px-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs font-mono">#{o.channel_id}</Badge>
                    <Badge variant="secondary" className="text-xs">
                      {PROVIDER_NAMES[o.provider] || o.provider}
                    </Badge>
                  </div>
                  <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-destructive hover:text-destructive" onClick={() => handleDelete(o)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
