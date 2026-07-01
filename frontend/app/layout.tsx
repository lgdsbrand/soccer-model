import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "WC2026 Predictor",
  description: "FIFA World Cup 2026 Predictions & Analytics",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ backgroundColor: "var(--bg-primary)" }}>
        <div style={{ display: "flex", minHeight: "100vh" }}>
          <Sidebar />
          <main className="px-4 pb-6 pt-20 md:px-6 md:pt-6 md:ml-[256px]" style={{ flex: 1, overflowY: "auto" }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
