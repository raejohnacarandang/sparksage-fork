"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { BookOpen, Save, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export default function DigestPage() {
  const { data: session } = useSession();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const [enabled, setEnabled] = useState(false);
  const [channelId, setChannelId] = useState("");
  const [digestTime, setDigestTime] = useState("09:00");

  const token = (session as { accessToken?: string })?.accessToken;

  useEffect(() => {
    if (!token) return;
    fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/config", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(({ config }) => {
        setEnabled(config.DIGEST_ENABLED === "true");
        setChannelId(config.DIGEST_CHANNEL_ID || "");
        setDigestTime(config.DIGEST_TIME || "09:00");
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token]);

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/config", {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          DIGEST_ENABLED: String(enabled),
          DIGEST_CHANNEL_ID: channelId,
          DIGEST_TIME: digestTime,
        }),
      });
      if (res.ok) {
        setMessage({ text: "Digest settings saved!", ok: true });
      } else {
        setMessage({ text: "Failed to save settings", ok: false });
      }
    } catch {
      setMessage({ text: "Error saving settings", ok: false });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-muted-foreground p-6">Loading...</p>;
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center gap-3">
        <BookOpen className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Daily Digest</h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Auto-post a daily AI summary of server activity
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

      <Card>
        <CardHeader>
          <CardTitle className="text-sm sm:text-base">Digest Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-sm font-medium">Enable Daily Digest</Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Automatically post a summary every day
              </p>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {/* Channel ID */}
          <div className="space-y-1">
            <Label htmlFor="digest-channel">Digest Channel ID</Label>
            <Input
              id="digest-channel"
              placeholder="e.g. 1234567890"
              value={channelId}
              onChange={(e) => setChannelId(e.target.value)}
              disabled={!enabled}
            />
            <p className="text-xs text-muted-foreground">
              Right-click a channel in Discord → Copy Channel ID
            </p>
          </div>

          {/* Time */}
          <div className="space-y-1">
            <Label htmlFor="digest-time">Post Time (UTC)</Label>
            <Input
              id="digest-time"
              type="time"
              value={digestTime}
              onChange={(e) => setDigestTime(e.target.value)}
              disabled={!enabled}
              className="w-36"
            />
            <p className="text-xs text-muted-foreground">
              Time in UTC when the digest is posted daily
            </p>
          </div>

          <Button onClick={handleSave} disabled={saving} size="sm">
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving..." : "Save Settings"}
          </Button>
        </CardContent>
      </Card>

      {/* Info card */}
      <Card className="border-dashed">
        <CardContent className="pt-4">
          <p className="text-xs text-muted-foreground">
            <strong>Tip:</strong> Use <code className="bg-muted px-1 rounded">/digest preview</code> in
            Discord to send a test digest immediately without waiting for the scheduled time.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
