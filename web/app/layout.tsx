import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Forma — A space to understand",
  description: "Explore connected ideas and follow your curiosity without losing your place.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
