/**
 * 历史消息转 Timeline 函数
 */

import type { Product } from "../core/payloads";
import type {
  TimelineState,
  LLMCallClusterItem,
  ContentSubItem,
  ProductsSubItem,
  LLMCallSubItem,
  HistoryMessage,
} from "./types";
import { createInitialState, insertItem } from "./helpers";
import { addUserMessage, addGreetingMessage } from "./actions";

export function historyToTimeline(messages: HistoryMessage[]): TimelineState {
  let state = createInitialState();

  for (const msg of messages) {
    if (msg.role === "user") {
      state = addUserMessage(state, msg.id, msg.content);
    } else if (msg.role === "system" && msg.message_type === "greeting") {
      const meta = msg.extra_metadata;
      state = addGreetingMessage(state, {
        id: msg.id,
        title: meta?.greeting_config?.title,
        subtitle: meta?.greeting_config?.subtitle,
        body: meta?.greeting_config?.body || msg.content,
        cta: meta?.cta,
        delayMs: meta?.delay_ms,
        channel: meta?.channel,
      });
    } else if (msg.role === "assistant") {
      const children: LLMCallSubItem[] = [];
      const childIndexById: Record<string, number> = {};

      const contentId = `${msg.id}-content`;
      const contentSubItem: ContentSubItem = {
        type: "content",
        id: contentId,
        text: msg.content,
        ts: Date.now(),
      };
      childIndexById[contentId] = children.length;
      children.push(contentSubItem);

      if (msg.products && msg.products.length > 0) {
        const productsId = `${msg.id}-products`;
        const productsSubItem: ProductsSubItem = {
          type: "products",
          id: productsId,
          products: msg.products,
          ts: Date.now(),
        };
        childIndexById[productsId] = children.length;
        children.push(productsSubItem);
      }

      const cluster: LLMCallClusterItem = {
        type: "llm.call.cluster",
        id: msg.id,
        turnId: msg.id,
        status: "success",
        children,
        childIndexById,
        ts: Date.now(),
      };
      state = insertItem(state, cluster);
    }
  }

  return state;
}
