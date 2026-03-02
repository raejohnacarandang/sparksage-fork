import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const providers: any[] = [
  Credentials({
    name: "Admin Password",
    credentials: {
      password: { label: "Password", type: "password" },
    },
    async authorize(credentials) {
      const adminPassword = process.env.ADMIN_PASSWORD;
      if (!adminPassword) return null;
      if (credentials?.password !== adminPassword) return null;

      try {
        // Get a real JWT from FastAPI
        const res = await fetch(`${API_URL}/api/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: credentials.password }),
        });

        if (!res.ok) return null;

        const data = await res.json();
        return {
          id: "admin",
          name: "Admin",
          email: "admin@sparksage.local",
          role: "admin",
          accessToken: data.access_token,
        };
      } catch {
        return null;
      }
    },
  }),
];

// Only add Discord provider if credentials are configured
if (process.env.DISCORD_CLIENT_ID && process.env.DISCORD_CLIENT_SECRET) {
  const Discord = require("next-auth/providers/discord").default;
  providers.push(
    Discord({
      clientId: process.env.DISCORD_CLIENT_ID,
      clientSecret: process.env.DISCORD_CLIENT_SECRET,
    })
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  callbacks: {
    async jwt({ token, account, profile, user }) {
      // Credentials login — store real JWT from FastAPI
      if (account?.provider === "credentials" && user) {
        token.accessToken = (user as any).accessToken;
        token.role = "admin";
        token.permissions = [
          "/dashboard",
          "/dashboard/providers",
          "/dashboard/settings",
          "/dashboard/conversations",
          "/dashboard/review",
          "/dashboard/analytics",
          "/dashboard/costs",
          "/dashboard/faq",
          "/dashboard/plugins",
          "/dashboard/permissions",
          "/dashboard/digest",
          "/dashboard/moderation",
          "/dashboard/channel-prompts",
          "/dashboard/channel-providers",
          "/dashboard/quota",
          "/dashboard/roles",
        ];
      }

      // Discord login
      if (account?.provider === "discord" && profile) {
        token.discord_id = profile.id as string;
        token.avatar = profile.image_url as string;
        token.accessToken = account.access_token as string;
        try {
          await fetch(`${API_URL}/api/roles/users`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              discord_id: profile.id,
              username: profile.username || profile.name,
              avatar: profile.image_url,
              role: "viewer",
            }),
          });
          const roleRes = await fetch(`${API_URL}/api/roles/me`, {
            headers: { Authorization: `Bearer ${token.accessToken}` },
          });
          if (roleRes.ok) {
            const data = await roleRes.json();
            token.role = data.role;
            token.permissions = data.permissions;
          }
        } catch {
          token.role = "viewer";
        }
      }

      return token;
    },

    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.user.role = (token.role as string) || "admin";
      session.user.permissions = token.permissions as string[];
      session.user.discord_id = token.discord_id as string;
      return session;
    },
  },

  pages: {
    signIn: "/login",
  },
});