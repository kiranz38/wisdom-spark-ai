import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WisdomBench — AI Wisdom Leaderboard",
  description:
    "How wise is your AI? Scoring the world's LLMs on cross-cultural wisdom, human dignity, compassion, and survival intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
