"""用一次性 SQLite 验证多 Agent 并发、会话隔离和中断回收，无外部模型请求。

运行：uv run python scripts/verify_chat_concurrency.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from langgraph_agent_kit import ChatContext, Orchestrator  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import get_db_context  # noqa: E402
from app.core.db.provider import SQLiteProvider  # noqa: E402
from app.models.agent import Agent  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.complaint_task import ComplaintTask  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.message import Message  # noqa: E402
from app.models.user import User  # noqa: E402
from app.routers.chat import chat, router  # noqa: E402
from app.schemas.agent import AgentConfig  # noqa: E402
from app.schemas.chat import ChatRequest  # noqa: E402
from app.schemas.complaint import ExecutorResult, PlannerDecision  # noqa: E402
from app.services.agent.core.service import AgentService  # noqa: E402
from app.services.agent.middleware.sequential_tools import (  # noqa: E402
    SequentialToolExecutionMiddleware,
)
from app.services.agent.middleware.todo_broadcast import TodoBroadcastMiddleware  # noqa: E402
from app.services.chat_runs import ChatRunCoordinator  # noqa: E402
from app.services.complaint.executor_service import ExecutorService  # noqa: E402
from app.services.complaint.planner_service import PlannerService  # noqa: E402


class ConnectedRequest:
    """保持直连生成器运行，便于检查返回的真实 SSE 与数据库状态。"""

    async def is_disconnected(self) -> bool:
        """本脚本通过关闭生成器和取消任务模拟断线。"""
        return False


async def collect(response) -> str:
    """消费响应，覆盖生成器正常完成时的清理行为。"""
    return "".join([str(chunk) async for chunk in response.body_iterator])


def context(identity: str) -> ChatContext:
    """创建运行隔离的上下文和可检查的事件发射器。"""
    return ChatContext(
        conversation_id=identity,
        user_id=f"user-{identity}",
        assistant_message_id=f"assistant-{identity}",
        emitter=SimpleNamespace(aemit=AsyncMock()),
    )


class ChatConcurrencyChecks(unittest.IsolatedAsyncioTestCase):
    """通过真实 SQLite 写入验证聊天主链路，不修改业务数据库。"""

    async def asyncSetUp(self) -> None:
        """建立独立数据库和四个互相隔离的 Agent、用户与会话。"""
        self.tmp = tempfile.TemporaryDirectory(prefix="embedease-concurrency-")
        self.provider = SQLiteProvider(f"sqlite+aiosqlite:///{self.tmp.name}/app.db")
        self.stack = ExitStack()
        self.stack.enter_context(patch("app.core.db.provider._provider", self.provider))
        self.coordinator = ChatRunCoordinator()
        self.stack.enter_context(patch("app.routers.chat.chat_run_coordinator", self.coordinator))
        self.stack.enter_context(patch.object(settings, "CHAT_MAX_CONCURRENT_RUNS", 16))
        self.stack.enter_context(patch(
            "app.services.support.handoff.HandoffService.notify_new_message", new=AsyncMock(),
        ))
        await self.provider.init_db(Base)
        async with get_db_context() as db:
            for name in ("a", "b", "ca", "cb"):
                complaint = name.startswith("c")
                db.add(User(id=f"u-{name}"))
                db.add(Agent(
                    id=name, name=f"Agent {name}", type="custom", status="enabled",
                    system_prompt=f"只使用 {name} 的资料", is_default=name == "a",
                    role_tag="executor" if complaint else None,
                    business_domain="complaint" if complaint else None,
                ))
                db.add(Conversation(id=f"conv-{name}", user_id=f"u-{name}", agent_id=name))
            for name, agent in (("a2", "a"), ("ca2", "ca")):
                db.add(User(id=f"u-{name}"))
                db.add(Conversation(id=f"conv-{name}", user_id=f"u-{name}", agent_id=agent))

    async def asyncTearDown(self) -> None:
        """等待独立通知任务退出后清理临时数据库和补丁。"""
        await asyncio.sleep(0)
        self.stack.close()
        await self.provider.close()
        self.tmp.cleanup()

    def request(self, name: str, **overrides) -> ChatRequest:
        """默认省略 Agent ID，验证服务继续使用会话绑定的 Agent。"""
        values = dict(user_id=f"u-{name}", conversation_id=f"conv-{name}", message="退款订单号12345678")
        return ChatRequest(**(values | overrides))

    async def messages(self, name: str) -> list[Message]:
        """读取落库事实，确认拒绝请求没有新增消息。"""
        async with get_db_context() as db:
            result = await db.execute(select(Message).where(Message.conversation_id == f"conv-{name}"))
            return list(result.scalars())

    async def test_complaint_models_overlap_without_database_transactions(self) -> None:
        """两套 Agent 的 Planner、Executor 都必须同时进入且未持有事务。"""
        planner_gate, executor_gate = asyncio.Event(), asyncio.Event()
        entered_plan, entered_executor = [], []
        check = self

        async def plan(service, **kwargs):
            check.assertFalse(service.session.in_transaction())
            entered_plan.append(kwargs["ticket"].conversation_id)
            if len(entered_plan) == 3:
                planner_gate.set()
            await asyncio.wait_for(planner_gate.wait(), 3)
            return PlannerDecision(
                assigned_agent_tag="resolution_execution_agent", task_type="resolution",
                goal="核实退款问题", success_criteria=["明确处理进展"],
                next_node_key="resolution", reasoning="信息齐全，核实退款进展",
            )

        async def execute(service, **kwargs):
            check.assertFalse(service.session.in_transaction())
            entered_executor.append(service.agent_config.agent_id)
            if len(entered_executor) == 3:
                executor_gate.set()
            await asyncio.wait_for(executor_gate.wait(), 3)
            return ExecutorResult(
                content=f"{service.agent_config.agent_id}：已记录退款问题，将核实订单并反馈处理进展。",
                collected_slots={"order_id": "12345678"}, task_completed=False,
            )

        with patch.object(PlannerService, "_plan_with_llm", plan), patch.object(
            ExecutorService, "_execute_with_llm", execute,
        ):
            responses = await asyncio.gather(*[chat(self.request(name), ConnectedRequest()) for name in ("ca", "cb", "ca2")])
            bodies = await asyncio.wait_for(asyncio.gather(*map(collect, responses)), 10)
        self.assertCountEqual(entered_executor, ["ca", "cb", "ca"])
        for name, body in zip(("ca", "cb", "ca2"), bodies):
            self.assertIn("assistant.final", body)
            self.assertNotIn('"type": "error"', body)
            saved = await self.messages(name)
            self.assertEqual(sorted(message.role for message in saved), ["assistant", "user"])
            self.assertIn(("ca" if name == "ca2" else name) + "：", next(message.content for message in saved if message.role == "assistant"))
        self.assertFalse(self.coordinator._active)

    async def test_regular_agents_overlap_and_keep_bound_agent(self) -> None:
        """普通 Agent 使用 SDK，两个会话的身份和最终消息互不串用。"""
        gate, entered = asyncio.Event(), []

        async def emit(**kwargs):
            ctx = kwargs["context"]
            entered.append((kwargs["agent_id"], ctx.user_id, ctx.conversation_id))
            if len(entered) == 3:
                gate.set()
            await asyncio.wait_for(gate.wait(), 3)
            await ctx.emitter.aemit("assistant.delta", {"delta": kwargs["agent_id"]})
            await ctx.emitter.aemit("__end__", None)

        with patch("app.routers.chat.get_agent_service", return_value=SimpleNamespace(chat_emit=emit)), patch(
            "app.routers.chat.ComplaintConversationOrchestrator",
        ) as complaint:
            responses = await asyncio.gather(*[chat(self.request(name), ConnectedRequest()) for name in ("a", "b", "a2")])
            await asyncio.wait_for(asyncio.gather(*map(collect, responses)), 5)
            complaint.assert_not_called()
        self.assertCountEqual(entered, [("a", "u-a", "conv-a"), ("b", "u-b", "conv-b"), ("a", "u-a2", "conv-a2")])
        for name in ("a", "b", "a2"):
            saved = await self.messages(name)
            self.assertEqual(next(message.content for message in saved if message.role == "assistant"), "a" if name == "a2" else name)

    async def test_http_rejections_preserve_status_and_retry_header(self) -> None:
        """通过 ASGI HTTP 验证客户端实际接收 409、503 及 Retry-After。"""
        app = FastAPI()
        app.include_router(router)
        with patch.object(settings, "CHAT_MAX_CONCURRENT_RUNS", 1):
            held = await chat(self.request("a"), ConnectedRequest())
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://check.local") as client:
                    duplicate = await client.post("/api/v1/chat", json=self.request("a").model_dump())
                    busy = await client.post("/api/v1/chat", json=self.request("b").model_dump())
                self.assertEqual(duplicate.status_code, 409)
                self.assertEqual(busy.status_code, 503)
                self.assertEqual(busy.headers["retry-after"], "5")
                self.assertIn("detail", busy.json())
            finally:
                await held.background()

    async def test_human_mode_skips_all_agent_execution(self) -> None:
        """人工模式继续转发消息，不进入普通 Agent 或客诉模型。"""
        async with get_db_context() as db:
            conversation = await db.get(Conversation, "conv-ca")
            conversation.handoff_state = "human"
        with patch("app.routers.chat.get_agent_service") as agent, patch(
            "app.routers.chat.ComplaintConversationOrchestrator",
        ) as complaint, patch("app.services.websocket.manager.ws_manager.send_to_role", new=AsyncMock()):
            body = await collect(await chat(self.request("ca"), ConnectedRequest()))
        self.assertIn("support.human_mode", body)
        agent.assert_not_called()
        complaint.assert_not_called()
        self.assertFalse(self.coordinator._active)

    async def test_closing_regular_stream_stops_agent_before_releasing_lease(self) -> None:
        """穿过路由、SDK 适配器和 SDK 的关闭链必须停止真实 producer。"""
        stopped = asyncio.Event()

        async def emit(**kwargs):
            try:
                await kwargs["context"].emitter.aemit("assistant.delta", {"delta": "开始"})
                await asyncio.Event().wait()
            finally:
                stopped.set()

        with patch("app.routers.chat.get_agent_service", return_value=SimpleNamespace(chat_emit=emit)):
            response = await chat(self.request("a"), ConnectedRequest())
            await anext(response.body_iterator)
            await anext(response.body_iterator)
            await anext(response.body_iterator)
            await response.body_iterator.aclose()
        self.assertTrue(stopped.is_set())
        self.assertFalse(self.coordinator._active)
        self.assertEqual([message.role for message in await self.messages("a")], ["user"])

    async def test_duplicate_and_overload_reject_before_writing(self) -> None:
        """运行名额覆盖未消费的响应，重复和超额请求不插入用户消息。"""
        with patch.object(settings, "CHAT_MAX_CONCURRENT_RUNS", 1):
            response = await chat(self.request("a"), ConnectedRequest())
            for name, status in (("a", 409), ("b", 503)):
                with self.assertRaises(HTTPException) as raised:
                    await chat(self.request(name), ConnectedRequest())
                self.assertEqual(raised.exception.status_code, status)
            self.assertEqual(len(await self.messages("a")), 1)
            self.assertFalse(await self.messages("b"))
            # 响应在尚未开始流式迭代时被 ASGI 结束，也必须清理。
            await response.background()
            response2 = await chat(self.request("b"), ConnectedRequest())
            await response2.background()
        self.assertFalse(self.coordinator._active)

    async def test_cross_agent_and_cross_user_are_rejected(self) -> None:
        """不能通过请求参数把其他用户或 Agent 的会话历史拿来执行。"""
        for changes, status in (({"agent_id": "b"}, 409), ({"user_id": "u-b"}, 404)):
            with self.assertRaises(HTTPException) as raised:
                await chat(self.request("a", **changes), ConnectedRequest())
            self.assertEqual(raised.exception.status_code, status)
        self.assertFalse(await self.messages("a"))
        self.assertFalse(self.coordinator._active)

    async def test_cancelling_complaint_releases_lease_and_marks_task_failed(self) -> None:
        """模型阶段取消后，已提交的任务不能继续显示 running。"""
        entered, stopped = asyncio.Event(), asyncio.Event()

        async def plan(service, **kwargs):
            self.assertFalse(service.session.in_transaction())
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

        with patch.object(PlannerService, "_plan_with_llm", plan):
            response = await chat(self.request("ca"), ConnectedRequest())
            await anext(response.body_iterator)
            running = asyncio.create_task(anext(response.body_iterator))
            await asyncio.wait_for(entered.wait(), 3)
            running.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await running
        self.assertTrue(stopped.is_set())
        self.assertFalse(self.coordinator._active)
        async with get_db_context() as db:
            tasks = list((await db.execute(select(ComplaintTask))).scalars())
            self.assertTrue(any(task.failure_reason == "run_interrupted" for task in tasks))
            self.assertFalse(any(task.status == "running" for task in tasks))

    async def test_asgi_disconnect_cleans_up_regular_and_complaint_runs(self) -> None:
        """使用 ASGI disconnect 触发 Starlette 取消域，检查实际响应清理链。"""
        app = FastAPI()
        app.include_router(router)
        for name in ("a", "ca"):
            entered, stopped = asyncio.Event(), asyncio.Event()
            sent_request = False

            async def wait_for_disconnect(**kwargs):
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    stopped.set()

            async def plan(service, **kwargs):
                return await wait_for_disconnect()

            async def receive():
                nonlocal sent_request
                if not sent_request:
                    sent_request = True
                    return {"type": "http.request", "body": json.dumps(self.request(name).model_dump()).encode(), "more_body": False}
                await entered.wait()
                return {"type": "http.disconnect"}

            async def send(message):
                """接受响应头和流片段；断开由 receive 单独驱动。"""

            scope = {
                "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1", "method": "POST", "scheme": "http",
                "path": "/api/v1/chat", "raw_path": b"/api/v1/chat", "query_string": b"",
                "root_path": "", "headers": [(b"content-type", b"application/json")],
                "client": ("127.0.0.1", 12345), "server": ("check.local", 80),
            }
            with patch("app.routers.chat.get_agent_service", return_value=SimpleNamespace(chat_emit=wait_for_disconnect)), patch.object(
                PlannerService, "_plan_with_llm", plan,
            ):
                await asyncio.wait_for(app(scope, receive, send), 5)
            self.assertTrue(stopped.is_set())
            self.assertFalse(self.coordinator._active)
        async with get_db_context() as db:
            tasks = list((await db.execute(select(ComplaintTask))).scalars())
            self.assertTrue(any(task.failure_reason == "run_interrupted" for task in tasks))
            self.assertFalse(any(task.status == "running" for task in tasks))


class AgentRuntimeChecks(unittest.IsolatedAsyncioTestCase):
    """验证共享 Agent 的构建、工具锁及事件状态都不会阻塞其他运行。"""

    async def test_agent_build_is_deduplicated_and_modes_are_separate(self) -> None:
        """相同 Agent 冷启动只构建一次，不同输出模式使用不同图。"""
        service = AgentService()
        config = AgentConfig(agent_id="cache-check", name="cache", type="custom", system_prompt="")

        @asynccontextmanager
        async def db():
            yield None

        async def build(**kwargs):
            await asyncio.sleep(0.01)
            return object()

        with patch.object(service, "_agents", {}), patch.object(service, "_agent_locks", {}), patch.object(
            service, "get_agent_config", new=AsyncMock(return_value=config),
        ), patch.object(service, "_get_checkpointer", new=AsyncMock()), patch(
            "app.services.agent.core.service.get_db_context", db,
        ), patch("app.services.agent.core.service.build_agent", side_effect=build) as factory:
            agents = await asyncio.gather(*[service.get_agent("cache-check") for _ in range(8)])
            self.assertTrue(all(agent is agents[0] for agent in agents))
            self.assertIsNot(await service.get_agent("cache-check", True), agents[0])
            self.assertEqual(factory.call_count, 2)
            service.invalidate_agent("cache-check")
            self.assertFalse(service._agents)

    async def test_tools_serialize_within_run_but_overlap_between_runs(self) -> None:
        """同轮工具保留顺序约束，其他用户的工具不再共用全局锁。"""
        middleware = SequentialToolExecutionMiddleware()
        gate, entered = asyncio.Event(), set()
        active, peak = {}, {}
        contexts = [context("a"), context("b")]

        async def handler(request):
            name = request.runtime.context.conversation_id
            active[name] = active.get(name, 0) + 1
            peak[name] = max(peak.get(name, 0), active[name])
            entered.add(name)
            if len(entered) == 2:
                gate.set()
            await asyncio.wait_for(gate.wait(), 2)
            await asyncio.sleep(0)
            active[name] -= 1

        calls = [middleware.awrap_tool_call(SimpleNamespace(
            tool_call={"name": "lookup"}, runtime=SimpleNamespace(context=ctx),
        ), handler) for ctx in contexts for _ in range(2)]
        await asyncio.gather(*calls)
        self.assertEqual(peak, {"a": 1, "b": 1})

    async def test_todo_deduplication_is_per_run(self) -> None:
        """两个用户有相同 TODO 时，两人都应收到各自的广播。"""
        middleware = TodoBroadcastMiddleware()
        for ctx in (context("a"), context("b")):
            for _ in range(2):
                await middleware.aafter_model({"todos": [{"content": "核实订单", "status": "pending"}]}, SimpleNamespace(context=ctx))
            ctx.emitter.aemit.assert_awaited_once()

    async def test_closing_sdk_stream_cancels_producer(self) -> None:
        """流关闭必须等实际 Agent 结束，避免释放名额后遗留后台运行。"""
        started, stopped = asyncio.Event(), asyncio.Event()

        async def run(message, context, **kwargs):
            started.set()
            try:
                await context.emitter.aemit("assistant.delta", {"delta": "开始"})
                await asyncio.Event().wait()
            finally:
                stopped.set()

        stream = Orchestrator(agent_runner=SimpleNamespace(run=run)).run(
            message="hello", conversation_id="a", user_id="u-a", assistant_message_id="m-a",
        )
        await anext(stream)
        await anext(stream)
        await stream.aclose()
        self.assertTrue(started.is_set())
        self.assertTrue(stopped.is_set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
