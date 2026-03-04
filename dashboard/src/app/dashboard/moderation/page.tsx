"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { ShieldAlert, Save, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export default function ModerationPage() {
  const { data: session } = useSession();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const [enabled, setEnabled] = useState(false);
  const [logChannelId, setLogChannelId] = useState("");
  const [sensitivity, setSensitivity] = useState("medium");

  const token = (session as { accessToken?: string })?.accessToken;

  useEffect(() => {
    if (!token) return;
    fetch("${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/config", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(({ config }) => {
        setEnabled(config.MODERATION_ENABLED === "true");
        setLogChannelId(config.MOD_LOG_CHANNEL_ID || "");
        setSensitivity(config.MODERATION_SENSITIVITY || "medium");
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
          MODERATION_ENABLED: String(enabled),
          MOD_LOG_CHANNEL_ID: logChannelId,
          MODERATION_SENSITIVITY: sensitivity,
        }),
      });
      if (res.ok) {
        setMessage({ text: "Moderation settings saved!", ok: true });
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
        <ShieldAlert className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Content Moderation</h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            AI-powered message flagging for moderator review
          </p>
        </div>
      </div>

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
          <CardTitle className="text-sm sm:text-base">Moderation Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-sm font-medium">Enable AI Moderation</Label>
              <p className="text-xs text-muted-foreground mt-0.5">
                Automatically flag suspicious messages for review
              </p>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {/* Log Channel */}
          <div className="space-y-1">
            <Label htmlFor="log-channel">Mod Log Channel ID</Label>
            <Input
              id="log-channel"
              placeholder="e.g. 1234567890"
              value={logChannelId}
              onChange={(e) => setLogChannelId(e.target.value)}
              disabled={!enabled}
            />
            <p className="text-xs text-muted-foreground">
              Channel where flagged messages are posted for review
            </p>
          </div>

          {/* Sensitivity */}
          <div className="space-y-2">
            <Label>Sensitivity Level</Label>
            <div className="flex gap-2 flex-wrap">
              {["low", "medium", "high"].map((level) => (
                <button
                  key={level}
                  onClick={() => setSensitivity(level)}
                  disabled={!enabled}
                  className={`px-4 py-1.5 rounded-lg text-sm border transition-colors capitalize
                    ${sensitivity === level
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background border-border hover:bg-muted"
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {level}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Low = obvious violations only · Medium = balanced · High = stricter flagging
            </p>
          </div>

          <Button onClick={handleSave} disabled={saving} size="sm">
            <Save className="mr-2 h-4 w-4" />
            {saving ? "Saving..." : "Save Settings"}
          </Button>
        </CardContent>
      </Card>

      <Card className="border-dashed">
        <CardContent className="pt-4">
          <p className="text-xs text-muted-foreground">
            <strong>Note:</strong> Moderation only flags messages for human review — no messages are
            automatically deleted. Use <code className="bg-muted px-1 rounded">/moderation test</code> in
            Discord to test the system on a sample message.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
