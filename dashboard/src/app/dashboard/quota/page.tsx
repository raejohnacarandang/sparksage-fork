"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Gauge, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface RateLimitConfig {
  rate_limit_user: number;
  rate_limit_guild: number;
}

interface UsageStat {
  id: string;
  type: "user" | "guild";
  requests_used: number;
  limit: number;
  remaining: number;
}

export default function QuotaPage() {
  const { data: session } = useSession();
  const [config, setConfig] = useState<RateLimitConfig>({ rate_limit_user: 10, rate_limit_guild: 30 });
  const [stats, setStats] = useState<UsageStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const token = (session as { accessToken?: string })?.accessToken;

  const fetchData = () => {
    if (!token) return;
    setLoading(true);

    fetch(`${API_URL}/api/config", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(({ config: cfg }) => {
        setConfig({
          rate_limit_user: Number(cfg.RATE_LIMIT_USER || 10),
          rate_limit_guild: Number(cfg.RATE_LIMIT_GUILD || 30),
        });
      })
      .catch(() => {});

    fetch(`${API_URL}/api/quota/stats", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        setStats(Array.isArray(data) ? data : []);
        setLastUpdated(new Date());
      })
      .catch(() => setStats([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, [token]);

  const userStats = stats.filter((s) => s.type === "user");
  const guildStats = stats.filter((s) => s.type === "guild");

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Gauge className="h-6 w-6 sm:h-7 sm:w-7 text-primary" />
          <div>
            <h1 className="text-xl sm:text-2xl font-bold">Quota Monitoring</h1>
            <p className="text-xs sm:text-sm text-muted-foreground">
              Rate limit usage per user and guild
            </p>
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`mr-2 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {lastUpdated && (
        <p className="text-xs text-muted-foreground">
          Last updated: {lastUpdated.toLocaleTimeString()}
        </p>
      )}

      {/* Config cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">User Rate Limit</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{config.rate_limit_user}</p>
            <p className="text-xs text-muted-foreground mt-1">requests per minute per user</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Guild Rate Limit</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{config.rate_limit_guild}</p>
            <p className="text-xs text-muted-foreground mt-1">requests per minute per guild</p>
          </CardContent>
        </Card>
      </div>

      {/* User usage */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm sm:text-base">Active Users (last 60s)</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : userStats.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active users in the last minute.</p>
          ) : (
            <div className="space-y-3">
              {userStats.map((s) => {
                const pct = (s.requests_used / s.limit) * 100;
                return (
                  <div key={s.id} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <code className="bg-muted px-1 rounded">{s.id}</code>
                      <div className="flex items-center gap-2">
                        <span>{s.requests_used}/{s.limit} requests</span>
                        <Badge variant={pct >= 80 ? "destructive" : "secondary"} className="text-xs">
                          {s.remaining} left
                        </Badge>
                      </div>
                    </div>
                    <Progress value={pct} />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Guild usage */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm sm:text-base">Active Guilds (last 60s)</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : guildStats.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active guilds in the last minute.</p>
          ) : (
            <div className="space-y-3">
              {guildStats.map((s) => {
                const pct = (s.requests_used / s.limit) * 100;
                return (
                  <div key={s.id} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <code className="bg-muted px-1 rounded">{s.id}</code>
                      <div className="flex items-center gap-2">
                        <span>{s.requests_used}/{s.limit} requests</span>
                        <Badge variant={pct >= 80 ? "destructive" : "secondary"} className="text-xs">
                          {s.remaining} left
                        </Badge>
                      </div>
                    </div>
                    <Progress value={pct} />
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
            Rate limits reset every 60 seconds using a sliding window algorithm.
            Configure limits via <code className="bg-muted px-1 rounded">RATE_LIMIT_USER</code> and{" "}
            <code className="bg-muted px-1 rounded">RATE_LIMIT_GUILD</code> in Settings.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
