/** 复现模型结束后发送商品的真实顺序，验证卡片不丢失且不污染下一轮。 */
import assert from "node:assert/strict";
import { createInitialState, startAssistantTurn, timelineReducer } from "../packages/chat-sdk/src/timeline/index";
import type { ChatEvent } from "../packages/chat-sdk/src/core/events";

let seq = 0;
function event(type: string, payload: Record<string, unknown>): ChatEvent {
  return { v: 1, id: `qa-${++seq}`, seq, ts: Date.now(), conversation_id: "qa", type, payload } as ChatEvent;
}
let state = startAssistantTurn(createInitialState(), "turn-one");
state = timelineReducer(state, event("llm.call.start", { llm_call_id: "call-one" }));
state = timelineReducer(state, event("llm.call.end", { llm_call_id: "call-one" }));
assert.equal(state.activeTurn.currentLlmCallId, null);
state = timelineReducer(state, event("assistant.products", { items: [{ id: "A", name: "演示商品", price: 129 }] }));
const cluster = state.timeline.find((item) => item.id === "call-one");
assert.equal(cluster?.type, "llm.call.cluster");
assert.ok(cluster?.type === "llm.call.cluster" && cluster.children.some((child) => child.type === "products" && child.products[0].id === "A"));
assert.equal(state.activeTurn.currentLlmCallId, null);
state = startAssistantTurn(state, "turn-two");
const before = JSON.stringify(state.timeline);
state = timelineReducer(state, event("assistant.products", { items: [{ id: "B", name: "另一商品" }] }));
assert.equal(JSON.stringify(state.timeline), before);
console.log("商品卡片延迟到达与跨轮隔离检查通过");
