import type { Metadata } from "next";
import { ThemeProvider } from "@/components/theme-provider";
import { FloatingChatWidget } from "@/components/features/embed";
import "./globals.css";

export const metadata: Metadata = {
  title: "商品推荐助手",
  description: "基于 AI 的智能商品推荐系统",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
          <FloatingChatWidget />
        </ThemeProvider>
      </body>
    </html>
  );
}
