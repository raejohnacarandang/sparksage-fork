import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Pages that require specific roles
const ROLE_ROUTES: Record<string, string[]> = {
  admin: [
    "/dashboard/providers",
    "/dashboard/settings",
    "/dashboard/costs",
    "/dashboard/plugins",
    "/dashboard/digest",
    "/dashboard/channel-prompts",
    "/dashboard/channel-providers",
    "/dashboard/quota",
    "/dashboard/review",
    "/dashboard/roles",
  ],
  moderator: [
    "/dashboard/faq",
    "/dashboard/permissions",
    "/dashboard/moderation",
    "/dashboard/conversations",
  ],
  viewer: [
    "/dashboard",
    "/dashboard/analytics",
  ],
};

function getRequiredRole(pathname: string): string {
  for (const [role, paths] of Object.entries(ROLE_ROUTES)) {
    if (paths.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
      return role;
    }
  }
  return "viewer";
}

function roleLevel(role: string): number {
  const levels: Record<string, number> = {
    viewer: 0,
    moderator: 1,
    admin: 2,
  };
  return levels[role] ?? 0;
}

export default auth((req) => {
  const { nextUrl, auth: session } = req as NextRequest & { auth: any };
  const pathname = nextUrl.pathname;

  // Skip non-dashboard routes
  if (!pathname.startsWith("/dashboard")) {
    return NextResponse.next();
  }

  // Not logged in — redirect to login
  if (!session) {
    return NextResponse.redirect(new URL("/login", nextUrl));
  }

  const userRole = session.user?.role || "viewer";
  const requiredRole = getRequiredRole(pathname);

  // Check if user has sufficient role level
  if (roleLevel(userRole) < roleLevel(requiredRole)) {
    return NextResponse.redirect(new URL("/dashboard?error=unauthorized", nextUrl));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/dashboard/:path*"],
};