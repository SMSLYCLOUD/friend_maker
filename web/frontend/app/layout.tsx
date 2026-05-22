import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SocialGrowthAI",
  description: "Premium AI-powered social media automation",
  viewport: "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no",
  themeColor: "#000000",
  appleWebApp: true,
  formatDetection: "telephone=no",
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
