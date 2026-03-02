"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import {
  Zap,
  LayoutDashboard,
  Cpu,
  Settings,
  MessageSquare,
  Wand2,
  LogOut,
  BarChart2,
  DollarSign,
  Puzzle,
  HelpCircle,
  ShieldCheck,
  BookOpen,
  ShieldAlert,
  MessageSquareDiff,
  Gauge,
  Shield,
  Code2,
  Hash,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";

const NAV_GROUPS = [
  {
    label: "General",
    items: [
      { title: "Overview", href: "/dashboard", icon: LayoutDashboard },
      { title: "Analytics", href: "/dashboard/analytics", icon: BarChart2 },
      { title: "Conversations", href: "/dashboard/conversations", icon: MessageSquare },
    ],
  },
  {
    label: "Configuration",
    items: [
      { title: "Providers", href: "/dashboard/providers", icon: Cpu },
      { title: "Settings", href: "/dashboard/settings", icon: Settings },
      { title: "Quota", href: "/dashboard/quota", icon: Gauge },
      { title: "Costs", href: "/dashboard/costs", icon: DollarSign },
    ],
  },
  {
    label: "Moderation",
    items: [
      { title: "FAQ", href: "/dashboard/faq", icon: HelpCircle },
      { title: "Moderation", href: "/dashboard/moderation", icon: ShieldAlert },
      { title: "Permissions", href: "/dashboard/permissions", icon: ShieldCheck },
    ],
  },
  {
    label: "Features",
    items: [
      { title: "Plugins", href: "/dashboard/plugins", icon: Puzzle },
      { title: "Review", href: "/dashboard/review", icon: Code2 },
      { title: "Digest", href: "/dashboard/digest", icon: BookOpen },
    ],
  },
  {
    label: "Advanced",
    items: [
      { title: "Channel Prompts", href: "/dashboard/channel-prompts", icon: MessageSquareDiff },
      { title: "Channel Providers", href: "/dashboard/channel-providers", icon: Hash },
      { title: "Roles", href: "/dashboard/roles", icon: Shield },
    ],
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Zap className="h-4 w-4" />
          </div>
          <span className="font-semibold">SparkSage</span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {NAV_GROUPS.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={
                        item.href === "/dashboard"
                          ? pathname === "/dashboard"
                          : pathname.startsWith(item.href)
                      }
                    >
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}

        {/* Tools */}
        <SidebarGroup>
          <SidebarGroupLabel>Tools</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={pathname === "/wizard"}
                >
                  <Link href="/wizard">
                    <Wand2 className="h-4 w-4" />
                    <span>Setup Wizard</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <Button
          variant="ghost"
          className="w-full justify-start"
          onClick={() => signOut({ callbackUrl: "/login" })}
        >
          <LogOut className="mr-2 h-4 w-4" />
          Sign Out
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}