import NextAuth from "next-auth";
import GithubProvider from "next-auth/providers/github";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function syncBackendUser(account: any, token: any) {
  if (!account?.provider || !account?.providerAccountId) return null;

  const provider = account.provider;
  const payload = {
    provider,
    provider_account_id: account.providerAccountId,
    github_id: provider === "github" ? account.providerAccountId : undefined,
    google_id: provider === "google" ? account.providerAccountId : undefined,
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
  });

  if (!response.ok) {
    throw new Error(`Backend auth sync failed with ${response.status}`);
  }

  return response.json();
}

const providers = [
  GithubProvider({
    clientId: process.env.GITHUB_ID || "",
    clientSecret: process.env.GITHUB_SECRET || "",
    authorization: { params: { scope: "read:user user:email repo" } },
  }),
];

const handler = NextAuth({
  providers,
  secret: process.env.NEXTAUTH_SECRET || "fallback-secret-for-dev",
  trustHost: true,
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        // Store GitHub access token for direct GitHub API calls
        if (account.access_token) {
          (token as any).accessToken = account.access_token;
        }
        try {
          const synced = await syncBackendUser(account, token);
          if (synced?.user_id) {
            (token as any).backendUserId = synced.user_id;
          }
          (token as any).provider = account.provider;
        } catch (error) {
          console.error("OBSIDIAN backend auth sync failed (non-blocking)", error);
          // Don't throw — allow login to proceed without backend sync
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
    }
  },
  pages: {
    signIn: '/',
  }
});

export { handler as GET, handler as POST };
