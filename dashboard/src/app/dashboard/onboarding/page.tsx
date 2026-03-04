"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Save, UserPlus, ToggleLeft, ToggleRight } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

const onboardingSchema = z.object({
  WELCOME_CHANNEL_ID: z.string(),
  WELCOME_MESSAGE: z.string().min(1, "Welcome message is required"),
  WELCOME_ENABLED: z.string(),
});

type OnboardingForm = z.infer<typeof onboardingSchema>;

const DEFAULTS: OnboardingForm = {
  WELCOME_CHANNEL_ID: "",
  WELCOME_MESSAGE: "Welcome {user} to {server}! Feel free to ask SparkSage anything.",
  WELCOME_ENABLED: "true",
};

export default function OnboardingPage() {
  const { data: session } = useSession();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const token = (session as { accessToken?: string })?.accessToken;

  const form = useForm<OnboardingForm>({
    resolver: zodResolver(onboardingSchema),
    defaultValues: DEFAULTS,
  });

  useEffect(() => {
    if (!token) return;
    api
      .getConfig(token)
      .then(({ config }) => {
        form.reset({
          WELCOME_CHANNEL_ID: config.WELCOME_CHANNEL_ID || "",
          WELCOME_MESSAGE: config.WELCOME_MESSAGE || DEFAULTS.WELCOME_MESSAGE,
          WELCOME_ENABLED: config.WELCOME_ENABLED || "true",
        });
      })
      .catch(() => toast.error("Failed to load onboarding settings"))
      .finally(() => setLoading(false));
  }, [token]);

  async function onSubmit(values: OnboardingForm) {
    if (!token) return;
    setSaving(true);
    try {
      await api.updateConfig(token, values);
      toast.success("Onboarding settings saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  const enabled = form.watch("WELCOME_ENABLED") === "true";
  const welcomeMessage = form.watch("WELCOME_MESSAGE");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <UserPlus className="h-6 w-6 text-purple-500" />
        <div>
          <h1 className="text-2xl font-bold">Member Onboarding</h1>
          <p className="text-sm text-muted-foreground">
            Configure welcome messages for new members
          </p>
        </div>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Enable/Disable Toggle */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Onboarding Status</CardTitle>
            <CardDescription>
              Enable or disable welcome messages for new members
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">
                  {enabled ? "Enabled" : "Disabled"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {enabled
                    ? "Welcome messages will be sent when members join"
                    : "No welcome messages will be sent"}
                </p>
              </div>
              <button
                type="button"
                onClick={() =>
                  form.setValue("WELCOME_ENABLED", enabled ? "false" : "true")
                }
                className="focus:outline-none"
              >
                {enabled ? (
                  <ToggleRight className="h-8 w-8 text-green-500" />
                ) : (
                  <ToggleLeft className="h-8 w-8 text-muted-foreground" />
                )}
              </button>
            </div>
          </CardContent>
        </Card>

        {/* Channel & Message */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Welcome Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="welcome-channel">Welcome Channel ID</Label>
              <Input
                id="welcome-channel"
                placeholder="e.g. 1234567890"
                {...form.register("WELCOME_CHANNEL_ID")}
              />
              <p className="text-xs text-muted-foreground">
                Right-click the channel in Discord → Copy Channel ID
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <Label htmlFor="welcome-message">Welcome Message</Label>
                <span className="text-xs text-muted-foreground">
                  {welcomeMessage?.length || 0} characters
                </span>
              </div>
              <Textarea
                id="welcome-message"
                rows={4}
                {...form.register("WELCOME_MESSAGE")}
              />
              {form.formState.errors.WELCOME_MESSAGE && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.WELCOME_MESSAGE.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Use{" "}
                <code className="bg-muted px-1 rounded">{"{user}"}</code> for
                the member's name and{" "}
                <code className="bg-muted px-1 rounded">{"{server}"}</code> for
                the server name
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Preview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Message Preview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg bg-muted p-4 text-sm">
              {welcomeMessage
                .replace("{user}", "@NewMember")
                .replace("{server}", "Your Server")}
            </div>
          </CardContent>
        </Card>

        <Button type="submit" disabled={saving} className="w-full">
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save Onboarding Settings
        </Button>
      </form>
    </div>
  );
}