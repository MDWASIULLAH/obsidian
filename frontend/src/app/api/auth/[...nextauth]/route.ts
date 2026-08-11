import NextAuth from "next-auth";
import GithubProvider from "next-auth/providers/github";

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL || "https://obsidian-backend-gute.onrender.com"
).replace(/\/$/, "");

async function syncBackendUser(account: any, token: any) {
  if (!account?.provider || !account?.providerAccountId) return null;

  const provider = account.provider;
  const payload = {
    provider,
    provider_account_id: account.providerAccountId,
    github_id: provider === "github" ? account.providerAccountId : undefined,
    username:
      token.name ||
      token.email ||
      `${provider}-${String(account.providerAccountId).slice(0, 8)}`,
    email: token.email,
    avatar_url: token.picture,
    access_token: provider === "github" ? account.access_token : undefined,
  };

  const response = await fetch(`${API_BASE}/api/v1/auth/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Backend auth sync failed with ${response.status}`);
  }

  return response.json();
}

const githubClientId = process.env.AUTH_GITHUB_ID || process.env.GITHUB_ID || "";
const githubClientSecret =
  process.env.AUTH_GITHUB_SECRET || process.env.GITHUB_SECRET || "";
const authSecret = process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET || "";

const providers = [
  GithubProvider({
    clientId: githubClientId,
    clientSecret: githubClientSecret,
    authorization: { params: { scope: "read:user user:email repo" } },
  }),
];

const handler = NextAuth({
  providers,
  secret: authSecret,
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        if (account.access_token) (token as any).accessToken = account.access_token;
        try {
          const synced = await syncBackendUser(account, token);
          if (synced?.user_id) (token as any).backendUserId = synced.user_id;
          (token as any).provider = account.provider;
        } catch (error) {
          console.error("OBSIDIAN backend auth sync failed (non-blocking)", error);
          (token as any).provider = account.provider;
        }
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).userId = (token as any).backendUserId;
      (session as any).provider = (token as any).provider;
      (session as any).accessToken = (token as any).accessToken;
      return session;
    },
    async redirect({ url, baseUrl }) {
      if (url.startsWith(baseUrl)) {
        const pathname = new URL(url).pathname;
        if (
          pathname === "/dashboard/setup" ||
          pathname === "/" ||
          pathname.startsWith("/api/auth")
        ) {
          return `${baseUrl}/dashboard`;
        }
        return url;
      }

      if (url.startsWith("/")) {
        if (url === "/dashboard/setup" || url.startsWith("/dashboard/setup/")) {
          return `${baseUrl}/dashboard`;
        }
        return `${baseUrl}${url}`;
      }

      return `${baseUrl}/dashboard`;
    },
  },
  pages: { signIn: "/" },
});

export { handler as GET, handler as POST };
