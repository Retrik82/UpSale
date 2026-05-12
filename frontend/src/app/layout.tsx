import type { Metadata } from "next";
import "./globals.css";
import { GlobalLanguageSwitcher } from "@/components/GlobalLanguageSwitcher";

export const metadata: Metadata = {
  title: "UpSale",
  description: "Record, transcribe and analyze your sales calls with AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-violet-50 antialiased">
        <GlobalLanguageSwitcher />
        {children}
      </body>
    </html>
  );
}
