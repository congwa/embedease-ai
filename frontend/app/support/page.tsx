"use client";

/** Landing preserves query-string deep links while leaving the mobile queue as the first screen. */
import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSupportWorkbenchStore } from "@/stores";

/** Opens a selected real conversation without inserting any demonstration data. */
function SupportInbox() {
  const router = useRouter();
  const params = useSearchParams();
  const conversations = useSupportWorkbenchStore(
    (store) => store.conversations,
  );
  const deepLink = params.get("conv_id") ?? params.get("conversation_id");
  useEffect(() => {
    if (deepLink) router.replace(`/support/${encodeURIComponent(deepLink)}`);
  }, [deepLink, router]);
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="flex size-16 items-center justify-center rounded-3xl border border-border bg-card">
        <Inbox className="size-7 text-muted-foreground" />
      </div>
      <h2 className="text-lg font-semibold">每一段对话，都值得被好好回应</h2>
      <p className="max-w-xs text-sm leading-6 text-muted-foreground">
        从左侧选择客户，查看对话和问题进展，开始处理当前会话。
      </p>
      {conversations[0] && (
        <Button
          className="mt-2 rounded-full"
          onClick={() =>
            router.push(`/support/${encodeURIComponent(conversations[0].id)}`)
          }
        >
          打开首个会话
        </Button>
      )}
    </div>
  );
}

/** Suspense isolates URL query access during the production build. */
export default function SupportPage() {
  return (
    <Suspense>
      <SupportInbox />
    </Suspense>
  );
}
