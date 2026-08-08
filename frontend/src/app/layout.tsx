import type { Metadata } from "next";
import "./globals.css";
import SessionProvider from "@/components/SessionProvider";

export const metadata: Metadata = {
  title: "OBSIDIAN — Autonomous Security Engineering",
  description:
    "An Autonomous AI Security Engineering Organization for the Secure Software Development Lifecycle.",
  keywords: [
    "security",
    "AI",
    "DevSecOps",
    "SDLC",
    "vulnerability",
    "threat modeling",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-surface-950 text-gray-100 antialiased">
        <SessionProvider>
          {children}
        </SessionProvider>
      </body>
    </html>
  );
}
