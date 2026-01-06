import { AdminSidebar } from "@/components/admin";
import { AgentProvider } from "@/contexts/agent-context";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AgentProvider>
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
        <AdminSidebar />
        <main className="ml-64 min-h-screen p-6">{children}</main>
      </div>
    </AgentProvider>
  );
}
