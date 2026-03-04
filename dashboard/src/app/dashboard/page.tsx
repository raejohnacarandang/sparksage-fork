"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useTheme } from "next-themes";
import {
  Activity, Cpu, Wifi, WifiOff, Server, ArrowRight, Radio,
  Sun, Moon, Bell, Search, Zap, RefreshCw, Settings,
  ShieldAlert, HelpCircle, BarChart2, X, BookOpen,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ProvidersResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

interface Guild {
  id: string;
  name: string;
  member_count: number;
}

interface WsBotStatus {
  online: boolean;
  latency_ms: number | null;
  guild_count: number;
  guilds: Guild[];
  username?: string | null;
}

interface ActivityEvent {
  id: number;
  event_type: string;
  user_id: string | null;
  username: string | null;        // ? add this
  channel_id: string | null;
  provider: string | null;
  latency_ms: number | null;
  created_at: string;
}

interface CommandCount {
  name: string;
  count: number;
}

interface Notification {
  id: number;
  text: string;
  type: string;
  time: string;
}

const QUICK_ACTIONS = [
  { label: "Moderation", href: "/dashboard/moderation", icon: ShieldAlert, color: "text-red-500" },
  { label: "FAQ", href: "/dashboard/faq", icon: HelpCircle, color: "text-yellow-500" },
  { label: "Analytics", href: "/dashboard/analytics", icon: BarChart2, color: "text-blue-500" },
  { label: "Digest", href: "/dashboard/digest", icon: BookOpen, color: "text-green-500" },
  { label: "Providers", href: "/dashboard/providers", icon: Cpu, color: "text-purple-500" },
  { label: "Settings", href: "/dashboard/settings", icon: Settings, color: "text-gray-500" },
];

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function eventColor(type: string): string {
  switch (type) {
    case "command": return "bg-blue-500";
    case "moderation": return "bg-red-500";
    case "faq": return "bg-green-500";
    case "onboarding": return "bg-purple-500";
    case "clear": return "bg-orange-500";
    case "summarize": return "bg-cyan-500";
    default: return "bg-gray-400";
  }
}

function eventText(event: ActivityEvent): string {
  const user = event.username
    ? `by @${event.username}`
    : event.user_id
    ? `by @${event.user_id}`
    : "";

  switch (event.event_type) {
    case "command": return `/ask used ${user}`.trim();
    case "clear": return `Conversation cleared ${user}`.trim();
    case "summarize": return `/summarize used ${user}`.trim();
    case "faq": return `FAQ matched ${user}`.trim();
    case "moderation": return `Moderation event in #${event.channel_id ?? "unknown"}`;
    case "provider_check": return `Provider check ${user}`.trim();
    default: return `${event.event_type} ${user}`.trim();
  }
}

export default function DashboardOverview() {
  const { data: session } = useSession();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [botStatus, setBotStatus] = useState<WsBotStatus | null>(null);
  const [providersData, setProvidersData] = useState<ProvidersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<typeof QUICK_ACTIONS>([]);
  const [commandData, setCommandData] = useState<CommandCount[]>([]);
  const [activityData, setActivityData] = useState<ActivityEvent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  const token = (session as { accessToken?: string })?.accessToken;
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!searchQuery.trim()) { setSearchResults([]); return; }
    const q = searchQuery.toLowerCase();
    setSearchResults(QUICK_ACTIONS.filter((a) => a.label.toLowerCase().includes(q)));
  }, [searchQuery]);

  // Load providers
  useEffect(() => {
    if (!token) return;
    api.getProviders(token).then((data) => { setProvidersData(data); setLoading(false); });
  }, [token]);

  // Load real analytics data
  useEffect(() => {
    if (!token) return;

    // Command usage from analytics summary
    api.getAnalytics(token).then((data) => {
      const byType: Record<string, number> = data.by_type || {};
      const commands: CommandCount[] = Object.entries(byType).map(([name, count]) => ({
        name: `/${name}`,
        count: count as number,
      })).sort((a, b) => b.count - a.count).slice(0, 6);
      setCommandData(commands);

      // Build notifications from real data
      const notifs: Notification[] = [];
      const totalEvents = Object.values(byType).reduce((a: number, b) => a + (b as number), 0);
      if (totalEvents > 0) {
        notifs.push({ id: 1, text: `${totalEvents} total events recorded`, type: "info", time: "now" });
      }
      if (data.avg_latency_ms) {
        const latency = data.avg_latency_ms;
        if (latency > 2000) {
          notifs.push({ id: 2, text: `High avg latency: ${latency}ms`, type: "warning", time: "now" });
        } else {
          notifs.push({ id: 2, text: `Avg response latency: ${latency}ms`, type: "info", time: "now" });
        }
      }
      setNotifications(notifs);
    }).catch(() => {});

    // Recent activity from analytics history
    fetch(
      `${API_URL}/api/analytics/history`,

      { headers: { Authorization: `Bearer ${token}` } }
    )
      .then((r) => r.json())
      .then((data) => {
        if (data.events) setActivityData(data.events.slice(0, 5));
      })
      .catch(() => {});
  }, [token]);

  const connectWs = useCallback(() => {
    if (!mountedRef.current) return;
    try {

      const wsUrl = apiUrl.replace(/^https/, "wss").replace(/^http/, "ws") + "/ws/stats";
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => { if (mountedRef.current) setWsConnected(true); };
      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          setBotStatus(data);
          setLastUpdated(new Date());
          setLoading(false);
        } catch {}
      };
      ws.onclose = () => {
        if (!mountedRef.current) return;
        setWsConnected(false);
        wsRef.current = null;
        reconnectTimer.current = setTimeout(() => { if (mountedRef.current) connectWs(); }, 5000);
      };
      ws.onerror = () => setWsConnected(false);
    } catch { setWsConnected(false); }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connectWs();
    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connectWs]);

  const primaryProvider = providersData?.providers.find((p) => p.is_primary);
  const guildsArray: Guild[] = botStatus?.guilds ?? [];
  const guildCount = botStatus?.guild_count ?? null;

  const latencyColor = botStatus?.latency_ms == null ? "text-muted-foreground"
    : botStatus.latency_ms < 100 ? "text-green-500"
    : botStatus.latency_ms < 200 ? "text-yellow-500" : "text-red-500";
  const latencyLabel = botStatus?.latency_ms == null ? ""
    : botStatus.latency_ms < 100 ? "Excellent"
    : botStatus.latency_ms < 200 ? "Good" : "High";

  return (
    <div className="space-y-4 sm:space-y-6 p-4 sm:p-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Overview</h1>
          {lastUpdated && (
            <p className="text-xs text-muted-foreground mt-0.5">
              Updated {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Search pages..."
              className="pl-8 h-9 w-40 sm:w-52 text-sm"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchResults.length > 0 && (
              <div className="absolute top-10 left-0 w-full bg-popover border rounded-lg shadow-lg z-50 py-1">
                {searchResults.map((r) => (
                  <Link key={r.href} href={r.href} className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted" onClick={() => setSearchQuery("")}>
                    <r.icon className={`h-4 w-4 ${r.color}`} />
                    {r.label}
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="relative">
            <Button variant="outline" size="icon" className="h-9 w-9 relative" onClick={() => setShowNotifications(!showNotifications)}>
              <Bell className="h-4 w-4" />
              {notifications.length > 0 && (
                <span className="absolute -top-1 -right-1 h-4 w-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center">
                  {notifications.length}
                </span>
              )}
            </Button>
            {showNotifications && (
              <div className="absolute right-0 top-11 w-72 bg-popover border rounded-lg shadow-lg z-50">
                <div className="flex items-center justify-between px-3 py-2 border-b">
                  <span className="text-sm font-medium">Notifications</span>
                  <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setShowNotifications(false)}>
                    <X className="h-3 w-3" />
                  </Button>
                </div>
                {notifications.length === 0 ? (
                  <p className="text-sm text-muted-foreground px-3 py-4 text-center">No notifications</p>
                ) : notifications.map((n) => (
                  <div key={n.id} className="px-3 py-2.5 border-b last:border-0 hover:bg-muted">
                    <p className="text-sm">{n.text}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{n.time}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <Button variant="outline" size="icon" className="h-9 w-9" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {mounted && (theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />)}
          </Button>

          <Badge variant={wsConnected ? "default" : "destructive"} className="flex items-center gap-1.5 text-xs">
            <Radio className={`h-3 w-3 ${wsConnected ? "animate-pulse" : ""}`} />
            {wsConnected ? "Live" : "Reconnecting..."}
          </Badge>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Bot Status</CardTitle>
            {botStatus?.online ? <Wifi className="h-4 w-4 text-green-600" /> : <WifiOff className="h-4 w-4 text-muted-foreground" />}
          </CardHeader>
          <CardContent>
            {loading ? <p className="text-sm text-muted-foreground">Connecting...</p> : (
              <div>
                <Badge variant={botStatus?.online ? "default" : "secondary"}>
                  {botStatus?.online ? "Online" : "Offline"}
                </Badge>
                {botStatus?.username && (
                  <p className="text-xs text-muted-foreground mt-1 truncate">{botStatus.username}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Latency</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${latencyColor}`}>
              {botStatus?.latency_ms != null ? `${Math.round(botStatus.latency_ms)}ms` : "--"}
            </p>
            {latencyLabel && <p className="text-xs text-muted-foreground mt-1">{latencyLabel}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Servers</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{guildCount ?? "--"}</p>
            <p className="text-xs text-muted-foreground mt-1">Discord servers</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">AI Provider</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {primaryProvider ? (
              <div>
                <p className="text-base font-semibold">{primaryProvider.display_name}</p>
                <p className="text-xs text-muted-foreground truncate">{primaryProvider.model}</p>
              </div>
            ) : <p className="text-sm text-muted-foreground">--</p>}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Zap className="h-4 w-4 text-yellow-500" />
            Quick Actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
            {QUICK_ACTIONS.map((action) => (
              <Link key={action.href} href={action.href} className="flex flex-col items-center gap-1.5 p-3 rounded-lg border hover:bg-muted transition-colors">
                <action.icon className={`h-5 w-5 ${action.color}`} />
                <span className="text-xs font-medium text-center">{action.label}</span>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Command Usage Chart + Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <BarChart2 className="h-4 w-4 text-blue-500" />
              Command Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            {commandData.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-12">No command data yet. Use the bot in Discord to see stats.</p>
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={commandData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {commandData.map((_, i) => (
                      <Cell key={i} fill={`hsl(${210 + i * 15}, 70%, 55%)`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-green-500" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {activityData.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-12">No recent activity. Use the bot in Discord to see events here.</p>
            ) : (
              <div className="space-y-2">
                {activityData.map((item, i) => (
                  <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted">
                    <span className={`h-2 w-2 rounded-full flex-shrink-0 ${eventColor(item.event_type)}`} />
                    <span className="text-sm flex-1 truncate">{eventText(item)}</span>
                    <span className="text-xs text-muted-foreground flex-shrink-0">{timeAgo(item.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Fallback Chain */}
      {providersData && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Fallback Chain</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-2">
              {providersData.fallback_order.map((name, i) => {
                const prov = providersData.providers.find((p) => p.name === name);
                return (
                  <div key={name} className="flex items-center gap-1 sm:gap-2">
                    <div className="flex items-center gap-1.5 rounded-lg border px-2 sm:px-3 py-1 sm:py-1.5">
                      <div className={`h-2 w-2 rounded-full flex-shrink-0 ${prov?.configured ? "bg-green-500" : "bg-gray-300"}`} />
                      <span className="text-xs sm:text-sm">{prov?.display_name || name}</span>
                      {prov?.is_primary && (
                        <Badge variant="secondary" className="ml-1 text-xs hidden sm:inline-flex">Primary</Badge>
                      )}
                    </div>
                    {i < providersData.fallback_order.length - 1 && (
                      <ArrowRight className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground" />
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connected Servers */}
      {guildsArray.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Connected Servers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {guildsArray.map((guild) => (
                <div key={guild.id} className="flex items-center justify-between rounded-lg border px-3 py-2">
                  <span className="text-sm font-medium truncate">{guild.name}</span>
                  <Badge variant="secondary" className="ml-2 flex-shrink-0 text-xs">
                    {guild.member_count} members
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

