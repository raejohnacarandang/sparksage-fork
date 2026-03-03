"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart2, MessageSquare, Zap, Cpu } from "lucide-react";
import { api } from "@/lib/api";

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"];

interface AnalyticsSummary {
  by_type: Record<string, number>;
  daily: { day: string; count: number }[];
  providers: { provider: string; count: number }[];
  total_messages: number;
  avg_latency_ms: number | null;
}

export default function AnalyticsPage() {
  const { data: session } = useSession();
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [costs, setCosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const token = (session as { accessToken?: string })?.accessToken;

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    api.getAnalytics(token)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));

    api.getAnalyticsCosts(token)
      .then((d) => setCosts(d.costs || []))
      .catch(console.error);
  }, [token]);

  const totalEvents = data ? Object.values(data.by_type).reduce((a, b) => a + b, 0) : 0;
  const byTypeData = data
    ? Object.entries(data.by_type).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <BarChart2 className="h-7 w-7 text-primary" />
        <h1 className="text-2xl font-bold">Analytics</h1>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading analytics...</p>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Total Events</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{totalEvents}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Total Messages</CardTitle>
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{data?.total_messages ?? "--"}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Avg Latency</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {data?.avg_latency_ms ? `${data.avg_latency_ms}ms` : "--"}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Providers Used</CardTitle>
                <Cpu className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{data?.providers.length ?? "--"}</p>
              </CardContent>
            </Card>
          </div>

          {/* Daily chart */}
          {data && data.daily.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Daily Activity (Last 30 Days)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={data.daily}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={false} name="Events" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {byTypeData.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Events by Type</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={byTypeData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="value" fill="#6366f1" name="Count" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}

            {data && data.providers.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Provider Usage</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={data.providers}
                        dataKey="count"
                        nameKey="provider"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {data.providers.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}
          </div>

          {totalEvents === 0 && (
            <Card>
              <CardContent className="pt-6 text-center text-muted-foreground">
                <BarChart2 className="h-10 w-10 mx-auto mb-3 opacity-30" />
                <p>No analytics data yet.</p>
                <p className="text-sm mt-1">Use bot commands in Discord to start collecting data.</p>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {costs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cost Tracking</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted-foreground border-b">
                  <th className="text-left pb-2">Provider</th>
                  <th className="text-left pb-2">Requests</th>
                  <th className="text-left pb-2">Tokens</th>
                  <th className="text-left pb-2">Est. Cost</th>
                  <th className="text-left pb-2">Tier</th>
                </tr>
              </thead>
              <tbody>
                {costs.map((c) => (
                  <tr key={c.provider} className="border-b last:border-0">
                    <td className="py-2 font-medium">{c.provider}</td>
                    <td className="py-2">{c.requests}</td>
                    <td className="py-2">{c.total_tokens}</td>
                    <td className="py-2">
                      {c.estimated_cost_usd === 0 ? "Free" : `$${c.estimated_cost_usd}`}
                    </td>
                    <td className="py-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        c.pricing_note === "Free tier"
                          ? "bg-green-100 text-green-700"
                          : "bg-orange-100 text-orange-700"
                      }`}>
                        {c.pricing_note}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}