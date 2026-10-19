/** Support routes share the production theme and preserve their queue across conversation navigation. */
import type { Metadata } from "next";
import type { ReactNode } from "react";
import SupportWorkspace from "./workspace";
import "./support-theme.css";

export const metadata: Metadata = {
  title: "客服工作台 · EmbedEase",
  description: "实时会话、人工接入与客诉处理工作台",
};

/** Keep route metadata server-rendered while the workspace owns real-time client state. */
export default function SupportLayout({ children }: { children: ReactNode }) {
  return <SupportWorkspace>{children}</SupportWorkspace>;
}
