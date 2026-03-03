"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { CheckCircle2, Loader2, Pencil } from "lucide-react";
import { useWizardStore } from "@/stores/wizard-store";
import { api } from "@/lib/api";
import { PROVIDER_INFO } from "@/types/provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function StepReview() {
  const router = useRouter();
  const { data: session } = useSession();
  const { data, setStep, reset } = useWizardStore();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>("");

  const token = (session as { accessToken?: string | unknown })?.accessToken;
  if (typeof token !== "string") {
    return <p className="text-sm text-destructive">Failed to load session</p>;
  }

  // Safely ensure data types
  const safeData = {
    discordToken: data.discordToken || "",
    botPrefix: data.botPrefix || "!",
    maxTokens: data.maxTokens || 1024,
    systemPrompt: data.systemPrompt || "",
    primaryProvider: data.primaryProvider || "",
    providers: data.providers || {},
  };

  const configuredProviders = Object.entries(safeData.providers)
    .filter(([, key]) => typeof key === "string" && key.length > 0)
    .map(([id]) => id);

  async function handleComplete() {
    if (!token) return;
    setSubmitting(true);
    setError("");

    try {
      // Build config payload
      const config: Record<string, string> = {
        discord_token: safeData.discordToken,
        ai_provider: safeData.primaryProvider,
        bot_prefix: safeData.botPrefix,
        max_tokens: String(safeData.maxTokens),
        system_prompt: safeData.systemPrompt,
      };

      // Add provider keys
      for (const [id, key] of Object.entries(safeData.providers)) {
        if (typeof key === "string" && key.length > 0) {
          config[`${id}_api_key`] = key;
        }
      }

      await api.completeWizard(token as string, config);
      reset();
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err) || "Failed to save configuration";
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Discord</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => setStep(0)}>
            <Pencil className="mr-1 h-3 w-3" /> Edit
          </Button>
        </CardHeader>
        <CardContent>
          <p className="text-sm font-mono">
            {safeData.discordToken ? `${safeData.discordToken.slice(0, 20)}...` : "Not configured"}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">AI Providers</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => setStep(1)}>
            <Pencil className="mr-1 h-3 w-3" /> Edit
          </Button>
        </CardHeader>
        <CardContent className="space-y-2">
          {configuredProviders.length === 0 ? (
            <p className="text-sm text-destructive">No providers configured</p>
          ) : (
            configuredProviders.map((id) => (
              <div key={id} className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <span className="text-sm">{PROVIDER_INFO[id]?.name || id}</span>
                {id === safeData.primaryProvider && (
                  <Badge variant="secondary">Primary</Badge>
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Bot Settings</CardTitle>
          <Button variant="ghost" size="sm" onClick={() => setStep(2)}>
            <Pencil className="mr-1 h-3 w-3" /> Edit
          </Button>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <p>
            <span className="text-muted-foreground">Prefix:</span> {String(safeData.botPrefix)}
          </p>
          <p>
            <span className="text-muted-foreground">Max tokens:</span> {String(safeData.maxTokens)}
          </p>
          <p>
            <span className="text-muted-foreground">System prompt:</span>{" "}
            {safeData.systemPrompt.length > 100
              ? `${safeData.systemPrompt.slice(0, 100)}...`
              : safeData.systemPrompt}
          </p>
        </CardContent>
      </Card>

      {error && <p className="text-sm text-destructive">{String(error)}</p>}

      <Button
        onClick={handleComplete}
        disabled={submitting || !safeData.discordToken || configuredProviders.length === 0}
        className="w-full"
        size="lg"
      >
        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Complete Setup
      </Button>
    </div>
  );
}
