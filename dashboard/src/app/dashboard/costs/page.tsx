"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { DollarSign, TrendingUp, AlertTriangle, Cpu } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

const ALERT_THRESHOLD = 0.8;

interface ProviderPricing {
  input_cost_per_1k: number;
  output_cost_per_1k: number;
  monthly_budget: number;
  free: boolean;
}

interface ProviderStat {
  provider: string;
  count: number;
  estimatedCost: number;
  monthlyProjection: number;
  limit: number;
  free: boolean;
}

const PROVIDER_NAMES: Record<string, string> = {
  gemini: "Google Gemini",
  groq: "Groq",
  openrouter: "OpenRouter",
  anthropic: "Anthropic Claude",
  openai: "OpenAI",
};

export default function CostTrackingPage() {
  const { data: session } = useSession();
  const [stats, setStats] = useState<ProviderStat[]>([]);
  const [pricing, setPricing] = useState<Record<string, ProviderPricing>>({});
  const [totalCost, setTotalCost] = useState(0);
  const [totalProjection, setTotalProjection] = useState(0);
  const [loading, setLoading] = useState(true);

  const token = (session as { accessToken?: string })?.accessToken;

  useEffect(() => {
    if (!token) return;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const pricingFetch = fetch(`${API_URL}/api/costs/pricing`, {
  headers: { Authorization: `Bearer ${token}` },
})
  .then((r) => r.json())
  .then((data) => { setPricing(data); return data; })
  .catch(() => ({}));

const analyticsFetch = fetch(`${API_URL}/api/analytics/summary`, {
  headers: { Authorization: `Bearer ${token}` },
})
  .then((r) => r.json())
  .catch(() => ({ providers: [] }));

    Promise.all([pricingFetch, analyticsFetch])
      .then(([pricingData, analyticsData]) => {
        const providerCounts: Record<string, number> = {};
        (analyticsData.providers || []).forEach(
          (p: { provider: string; count: number }) => {
            if (p.provider) providerCounts[p.provider] = p.count;
          }
        );

        const providerStats: ProviderStat[] = Object.entries(providerCounts).map(
          ([provider, count]) => {
            const p: ProviderPricing = pricingData[provider] || {
              input_cost_per_1k: 0,
              output_cost_per_1k: 0,
              monthly_budget: 0,
              free: true,
            };
            const estimatedTokens = count * 500;
            const avgCostPer1k = (p.input_cost_per_1k + p.output_cost_per_1k) / 2;
            const estimatedCost = (estimatedTokens / 1000) * avgCostPer1k;
            const monthlyProjection = estimatedCost * (30 / 7);
            return {
              provider,
              count,
              estimatedCost,
              monthlyProjection,
              limit: p.monthly_budget,
              free: p.free,
            };
          }
        );

        setStats(providerStats);
        setTotalCost(providerStats.reduce((s, p) => s + p.estimatedCost, 0));
        setTotalProjection(providerStats.reduce((s, p) => s + p.monthlyProjection, 0));
      })
      .finally(() => setLoading(false));
  }, [token]);

  const alertProviders = stats.filter(
    (p) => p.limit > 0 && p.monthlyProjection / p.limit >= ALERT_THRESHOLD
  );

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center gap-3">
        <DollarSign className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Cost Tracking</h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Provider usage and estimated API costs
          </p>
        </div>
      </div>

      {/* Alert banner */}
      {alertProviders.length > 0 && (
        <Card className="border-orange-400 bg-orange-50 dark:bg-orange-950/20">
          <CardContent className="pt-4">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-orange-700 dark:text-orange-400">
                  Cost Alert
                </p>
                <p className="text-xs text-orange-600 dark:text-orange-500 mt-0.5">
                  {alertProviders.map((p) => PROVIDER_NAMES[p.provider] || p.provider).join(", ")}{" "}
                  {alertProviders.length === 1 ? "is" : "are"} approaching the monthly budget threshold.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Estimated This Period</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">${totalCost.toFixed(4)}</p>
            <p className="text-xs text-muted-foreground mt-1">Last ~7 days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Projected Monthly</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">${totalProjection.toFixed(4)}</p>
            <p className="text-xs text-muted-foreground mt-1">Based on current usage</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Active Providers</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{stats.length}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {stats.filter((p) => p.free).length} free,{" "}
              {stats.filter((p) => !p.free).length} paid
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Per-provider breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm sm:text-base">Cost Per Provider</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : stats.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <DollarSign className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p>No usage data yet.</p>
              <p className="text-xs mt-1">Start using bot commands to see cost tracking.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {stats.map((stat) => {
                const p = pricing[stat.provider];
                const usagePercent =
                  stat.limit > 0
                    ? Math.min((stat.monthlyProjection / stat.limit) * 100, 100)
                    : 0;
                const isAlert = stat.limit > 0 && usagePercent >= ALERT_THRESHOLD * 100;

                return (
                  <div key={stat.provider} className="space-y-2">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">
                          {PROVIDER_NAMES[stat.provider] || stat.provider}
                        </span>
                        <Badge variant={stat.free ? "secondary" : "outline"} className="text-xs">
                          {stat.free ? "Free" : "Paid"}
                        </Badge>
                        {isAlert && (
                          <Badge variant="destructive" className="text-xs">
                            ?? Alert
                          </Badge>
                        )}
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-semibold">
                          ${stat.estimatedCost.toFixed(4)}
                        </span>
                        <span className="text-xs text-muted-foreground ml-2">
                          (~${stat.monthlyProjection.toFixed(2)}/mo projected)
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-muted-foreground">
                      <span>Requests: <strong>{stat.count}</strong></span>
                      <span>~Tokens: <strong>{(stat.count * 500).toLocaleString()}</strong></span>
                      <span>Input rate: <strong>${p?.input_cost_per_1k ?? 0}/1k</strong></span>
                      <span>Budget: <strong>{stat.limit > 0 ? `$${stat.limit}/mo` : "Unlimited"}</strong></span>
                    </div>

                    {stat.limit > 0 && (
                      <div className="space-y-1">
                        <Progress value={usagePercent} />
                        <p className="text-xs text-muted-foreground">
                          {usagePercent.toFixed(1)}% of monthly budget used
                        </p>
                      </div>
                    )}

                    <div className="border-b last:border-0" />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-dashed">
        <CardContent className="pt-4">
          <p className="text-xs text-muted-foreground">
            <strong>Note:</strong> Gemini, Groq, and OpenRouter are free-tier providers with no API cost.
            Cost tracking applies only to paid providers (Anthropic, OpenAI). Token counts are estimated
            at ~500 tokens per request. Pricing is sourced from <code>config.py</code>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

