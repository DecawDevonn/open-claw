"""Tests for the multi-agent skeleton — agents, channels, gateway, delivery,
orchestration, memory, loggers, queues, config, and tools."""

from __future__ import annotations

import asyncio
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Agents
# ═══════════════════════════════════════════════════════════════════════════════

class TestBaseAgent:
    def test_process_raises(self):
        from agents.base_agent import BaseAgent
        agent = BaseAgent()
        with pytest.raises(NotImplementedError):
            agent.process("hello", "session-1")

    def test_proactive_tasks_noop(self):
        from agents.base_agent import BaseAgent
        BaseAgent().perform_proactive_tasks()  # must not raise

    def test_to_dict(self):
        from agents.base_agent import BaseAgent
        d = BaseAgent().to_dict()
        assert "name" in d and "type" in d


class TestDefaultAgent:
    def test_process_returns_string(self):
        from agents.default_agent import DefaultAgent
        agent = DefaultAgent()
        reply = agent.process("anything", "sess-1")
        assert isinstance(reply, str) and len(reply) > 0

    def test_name(self):
        from agents.default_agent import DefaultAgent
        assert DefaultAgent.name == "default"


class TestWeatherAgent:
    def test_extract_location_with_keyword(self):
        from agents.weather_agent import WeatherAgent
        agent = WeatherAgent()
        loc = agent._extract_location("weather in Tokyo")
        assert "Tokyo" in loc

    def test_extract_location_fallback(self):
        from agents.weather_agent import WeatherAgent
        agent = WeatherAgent()
        loc = agent._extract_location("what is the weather like?")
        assert isinstance(loc, str)

    def test_keywords(self):
        from agents.weather_agent import WeatherAgent
        assert "weather" in WeatherAgent.keywords

    def test_format_weather(self):
        from agents.weather_agent import WeatherAgent
        data = {"current_weather": {"temperature": 22, "windspeed": 15, "weathercode": 0}}
        result = WeatherAgent._format_weather(data, "Berlin")
        assert "22" in result and "Berlin" in result


class TestEmailAgent:
    def test_dry_run_no_tool(self):
        from agents.email_agent import EmailAgent
        agent = EmailAgent()
        reply = agent.process("To: test@example.com\nSubject: Hi\nHello!", "sess-1")
        assert "dry-run" in reply.lower() or "test@example.com" in reply

    def test_proactive_tasks_noop(self):
        from agents.email_agent import EmailAgent
        EmailAgent().perform_proactive_tasks()

    def test_parse_request(self):
        from agents.email_agent import EmailAgent
        to, subject, _ = EmailAgent._parse_request("To: alice@example.com\nSubject: Test\nBody here")
        assert to == "alice@example.com"
        assert subject == "Test"


# ═══════════════════════════════════════════════════════════════════════════════
# Gateway — Router
# ═══════════════════════════════════════════════════════════════════════════════

class TestRouter:
    def setup_method(self):
        # Reset global registry between tests
        import gateway.router as r
        r._registry.clear()
        r._fallback = None

    def _make_msg(self, content="hello", session_id="s1", source="web"):
        return type("Msg", (), {"content": content, "session_id": session_id, "source": source})()

    def test_no_match_returns_default_agent(self):
        from gateway.router import route_message
        from agents.default_agent import DefaultAgent
        agent = route_message(self._make_msg("random text"))
        assert isinstance(agent, DefaultAgent)

    def test_keyword_match(self):
        from gateway.router import route_message, register_agent
        from agents.weather_agent import WeatherAgent
        register_agent(WeatherAgent())
        agent = route_message(self._make_msg("weather in Paris"))
        assert isinstance(agent, WeatherAgent)

    def test_fallback_used_when_no_keyword(self):
        from gateway.router import route_message, set_fallback
        from agents.default_agent import DefaultAgent
        fallback = DefaultAgent()
        set_fallback(fallback)
        agent = route_message(self._make_msg("unrelated message"))
        assert agent is fallback

    def test_register_and_route_email(self):
        from gateway.router import route_message, register_agent
        from agents.email_agent import EmailAgent
        register_agent(EmailAgent())
        agent = route_message(self._make_msg("send email to alice"))
        assert isinstance(agent, EmailAgent)


# ═══════════════════════════════════════════════════════════════════════════════
# Gateway — Dispatcher
# ═══════════════════════════════════════════════════════════════════════════════

class TestDispatcher:
    def test_dispatch_missing_keys_raises(self):
        from gateway.dispatcher import Dispatcher
        dispatcher = Dispatcher()
        with pytest.raises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                dispatcher.dispatch({"content": "hi"})
            )

    def test_dispatch_no_queue_logs_warning(self):
        from gateway.dispatcher import Dispatcher
        dispatcher = Dispatcher(queue=None)
        msg = {"content": "hi", "session_id": "1", "source": "web"}
        # Should not raise even without a queue
        asyncio.get_event_loop().run_until_complete(dispatcher.dispatch(msg))

    def test_dispatch_with_mock_queue(self):
        enqueued = []

        class MockQueue:
            async def enqueue(self, msg):
                enqueued.append(msg)

        from gateway.dispatcher import Dispatcher
        dispatcher = Dispatcher(queue=MockQueue())
        msg = {"content": "hello", "session_id": "s1", "source": "telegram"}
        asyncio.get_event_loop().run_until_complete(dispatcher.dispatch(msg))
        assert len(enqueued) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Channels
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelegramChannel:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_empty_message_skipped(self):
        from channels.telegram_channel import TelegramChannel
        dispatched = []

        class MockDispatcher:
            async def dispatch(self, msg):
                dispatched.append(msg)

        channel = TelegramChannel(dispatcher=MockDispatcher())
        self._run(channel.handle_update({"message": {"text": "", "chat": {"id": 1}}}))
        assert dispatched == []

    def test_valid_update_dispatched(self):
        from channels.telegram_channel import TelegramChannel
        dispatched = []

        class MockDispatcher:
            async def dispatch(self, msg):
                dispatched.append(msg)

        channel = TelegramChannel(dispatcher=MockDispatcher())
        update = {"message": {"text": "Hello!", "chat": {"id": 123}}}
        self._run(channel.handle_update(update))
        assert len(dispatched) == 1
        assert dispatched[0]["content"] == "Hello!"
        assert dispatched[0]["source"] == "telegram"

    def test_no_message_field_skipped(self):
        from channels.telegram_channel import TelegramChannel
        channel = TelegramChannel()
        self._run(channel.handle_update({"inline_query": {}}))  # no message field


class TestSlackChannel:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_non_message_event_ignored(self):
        from channels.slack_channel import SlackChannel
        dispatched = []

        class MockDispatcher:
            async def dispatch(self, msg):
                dispatched.append(msg)

        channel = SlackChannel(dispatcher=MockDispatcher())
        self._run(channel.handle_event({"event": {"type": "reaction_added"}}))
        assert dispatched == []

    def test_valid_message_dispatched(self):
        from channels.slack_channel import SlackChannel
        dispatched = []

        class MockDispatcher:
            async def dispatch(self, msg):
                dispatched.append(msg)

        channel = SlackChannel(dispatcher=MockDispatcher())
        payload = {"event": {"type": "message", "text": "hi", "channel": "C123", "user": "U456"}}
        self._run(channel.handle_event(payload))
        assert len(dispatched) == 1
        assert dispatched[0]["content"] == "hi"

    def test_bot_message_ignored(self):
        from channels.slack_channel import SlackChannel
        dispatched = []

        class MockDispatcher:
            async def dispatch(self, msg):
                dispatched.append(msg)

        channel = SlackChannel(dispatcher=MockDispatcher())
        payload = {"event": {"type": "message", "text": "bot reply", "bot_id": "B1", "channel": "C1"}}
        self._run(channel.handle_event(payload))
        assert dispatched == []


class TestWebChannel:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_empty_message_raises(self):
        from channels.web_channel import WebChannel
        channel = WebChannel()
        with pytest.raises(ValueError):
            self._run(channel.handle_request({"message": ""}))

    def test_valid_request_returns_session_id(self):
        from channels.web_channel import WebChannel
        dispatched = []

        class MockDispatcher:
            async def dispatch(self, msg):
                dispatched.append(msg)

        channel = WebChannel(dispatcher=MockDispatcher())
        sid = self._run(channel.handle_request({"message": "Hello"}))
        assert isinstance(sid, str) and len(sid) > 0
        assert dispatched[0]["source"] == "web"


# ═══════════════════════════════════════════════════════════════════════════════
# Delivery
# ═══════════════════════════════════════════════════════════════════════════════

class TestFormatters:
    def test_slack_bold_conversion(self):
        from delivery.formatters import format_response
        result = format_response("**bold text**", "slack")
        assert result == "*bold text*"

    def test_voice_strips_markdown(self):
        from delivery.formatters import format_response
        result = format_response("## Heading\n**bold** and _italic_", "voice")
        assert "##" not in result
        assert "**" not in result
        assert "_" not in result

    def test_telegram_passthrough(self):
        from delivery.formatters import format_response
        result = format_response("  hello world  ", "telegram")
        assert result == "hello world"

    def test_unknown_source_strips_markdown(self):
        from delivery.formatters import format_response
        result = format_response("**bold**", "unknown_channel")
        assert "**" not in result


class TestMessenger:
    def test_send_no_channel_does_not_raise(self):
        from delivery.messenger import Messenger
        messenger = Messenger()
        messenger.send("hello", "unknown_source", "session-1")  # should not raise

    def test_send_with_registered_channel(self):
        from delivery.messenger import Messenger, register_channel
        sent = []

        class FakeChannel:
            def send(self, session_id, text):
                sent.append((session_id, text))

        register_channel("test_ch", FakeChannel())
        messenger = Messenger()
        messenger.send("reply text", "test_ch", "user-99")
        assert len(sent) == 1
        assert sent[0] == ("user-99", "reply text")


class TestRetryQueue:
    def test_enqueue_and_flush_delivery(self):
        from delivery.retry_queue import RetryQueue

        delivered = []

        class FakeMessenger:
            def send(self, response, source, session_id):
                delivered.append((source, session_id, response))

        rq = RetryQueue(messenger=FakeMessenger())
        rq.enqueue("hello", "web", "s1")
        assert rq.size() == 1
        count = rq.flush()
        assert count == 1
        assert rq.size() == 0
        assert delivered[0] == ("web", "s1", "hello")

    def test_max_retries_drops_entry(self):
        from delivery.retry_queue import RetryQueue

        class FailingMessenger:
            def send(self, response, source, session_id):
                raise RuntimeError("network error")

        rq = RetryQueue(messenger=FailingMessenger())
        rq.enqueue("msg", "telegram", "s2", max_attempts=1)
        # First flush: attempt 1 (fails), entry has 1 attempt == max_attempts → dropped
        rq.flush()
        assert rq.size() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Memory
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionStore:
    def test_get_or_create(self):
        from memory.session_store import SessionStore
        store = SessionStore()
        s = store.get_or_create("user-1")
        assert "messages" in s and "metadata" in s

    def test_append_and_retrieve_messages(self):
        from memory.session_store import SessionStore
        store = SessionStore()
        store.append_message("u1", "user", "hello")
        store.append_message("u1", "assistant", "hi there")
        msgs = store.get_messages("u1")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["content"] == "hi there"

    def test_limit_messages(self):
        from memory.session_store import SessionStore
        store = SessionStore()
        for i in range(10):
            store.append_message("u2", "user", f"msg{i}")
        assert len(store.get_messages("u2", limit=3)) == 3

    def test_clear_messages(self):
        from memory.session_store import SessionStore
        store = SessionStore()
        store.append_message("u3", "user", "data")
        store.clear_messages("u3")
        assert store.get_messages("u3") == []

    def test_set_and_get_meta(self):
        from memory.session_store import SessionStore
        store = SessionStore()
        store.set_meta("u4", "lang", "en")
        assert store.get_meta("u4", "lang") == "en"

    def test_cleanup_ttl(self):
        from memory.session_store import SessionStore
        import time
        store = SessionStore(ttl=0.01)   # 10 ms TTL
        store.get_or_create("u5")
        time.sleep(0.05)
        removed = store.cleanup()
        assert removed == 1

    def test_delete_session(self):
        from memory.session_store import SessionStore
        store = SessionStore()
        store.get_or_create("u6")
        assert store.delete("u6") is True
        assert store.get("u6") is None

    def test_get_nonexistent_returns_none(self):
        from memory.session_store import SessionStore
        assert SessionStore().get("missing") is None


class TestContextManager:
    def test_build_context_includes_system(self):
        from memory.context_manager import ContextManager
        cm = ContextManager(system_prompt="You are a bot.")
        cm.add_user_message("s1", "Hello")
        ctx = cm.build_context("s1")
        assert ctx[0]["role"] == "system"
        assert ctx[0]["content"] == "You are a bot."
        assert ctx[1]["role"] == "user"

    def test_summarise(self):
        from memory.context_manager import ContextManager
        cm = ContextManager()
        cm.add_user_message("s1", "Hi!")
        cm.add_assistant_message("s1", "Hello!")
        summary = cm.summarise("s1")
        assert "User" in summary and "Assistant" in summary

    def test_clear_resets_history(self):
        from memory.context_manager import ContextManager
        cm = ContextManager()
        cm.add_user_message("s2", "test")
        cm.clear("s2")
        ctx = cm.build_context("s2")
        # Only system prompt remains
        assert len(ctx) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Loggers
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogger:
    def test_get_logger(self):
        from loggers.logger import get_logger
        log = get_logger("test.module")
        assert log.name == "test.module"

    def test_log_functions_do_not_raise(self):
        from loggers.logger import log_info, log_error, log_warning, log_debug
        log_info("info message")
        log_error("error message")
        log_warning("warning message")
        log_debug("debug message")


class TestMetrics:
    def test_increment_and_count(self):
        from loggers.metrics import MetricsCollector
        m = MetricsCollector()
        m.increment("requests")
        m.increment("requests")
        assert m.count("requests") == 2.0

    def test_gauge(self):
        from loggers.metrics import MetricsCollector
        m = MetricsCollector()
        m.gauge("queue_depth", 7)
        assert m.get_gauge("queue_depth") == 7.0

    def test_snapshot_keys(self):
        from loggers.metrics import MetricsCollector
        m = MetricsCollector()
        snap = m.snapshot()
        assert "counters" in snap and "gauges" in snap and "uptime_seconds" in snap

    def test_tags_in_key(self):
        from loggers.metrics import MetricsCollector
        m = MetricsCollector()
        m.increment("messages", tags={"channel": "telegram"})
        assert m.count("messages", tags={"channel": "telegram"}) == 1.0
        assert m.count("messages", tags={"channel": "slack"}) == 0.0

    def test_reset(self):
        from loggers.metrics import MetricsCollector
        m = MetricsCollector()
        m.increment("x")
        m.gauge("y", 5)
        m.reset()
        assert m.count("x") == 0.0
        assert m.get_gauge("y") == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Queues — RedisQueue (no live Redis required)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedisQueue:
    def test_empty_channel_raises(self):
        from queues.redis_queue import RedisQueue
        with pytest.raises(ValueError):
            RedisQueue(channel="")

    def test_assert_connected_raises(self):
        from queues.redis_queue import RedisQueue
        q = RedisQueue()
        with pytest.raises(RuntimeError):
            asyncio.get_event_loop().run_until_complete(q.dequeue())

    def test_enqueue_dequeue_mock(self):
        """Test queue logic without a live Redis by injecting a fake client."""
        from queues.redis_queue import RedisQueue
        import json

        q = RedisQueue()
        # Inject an in-memory fake redis client
        store = []

        class FakeRedis:
            async def rpush(self, channel, value):
                store.append(value)

            async def lpop(self, channel):
                return store.pop(0) if store else None

            async def llen(self, channel):
                return len(store)

            async def delete(self, channel):
                store.clear()

        q._redis = FakeRedis()

        async def _test():
            await q.enqueue({"content": "hello", "session_id": "s1"})
            result = await q.dequeue()
            assert result["content"] == "hello"
            empty = await q.dequeue()
            assert empty is None

        asyncio.get_event_loop().run_until_complete(_test())


# ═══════════════════════════════════════════════════════════════════════════════
# Config / Settings
# ═══════════════════════════════════════════════════════════════════════════════

class TestSettings:
    def test_defaults(self):
        from config.settings import Settings
        s = Settings()
        assert s.host == "0.0.0.0"
        assert s.port == 8080
        assert s.jwt_algorithm == "HS256"
        assert s.queue_channel == "openclaw:messages"

    def test_get_settings_singleton(self):
        import config.settings as cs
        cs._instance = None  # reset
        s1 = cs.get_settings()
        s2 = cs.get_settings()
        assert s1 is s2

    def test_warn_insecure_defaults_does_not_raise(self):
        from config.settings import Settings
        Settings().warn_insecure_defaults()


# ═══════════════════════════════════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════════════════════════════════

class TestBaseTool:
    def test_execute_raises(self):
        from tools.base_tool import BaseTool
        with pytest.raises(NotImplementedError):
            BaseTool().execute()

    def test_call_validates_then_executes(self):
        from tools.base_tool import BaseTool

        class EchoTool(BaseTool):
            name = "echo"

            def execute(self, text=""):
                return text

        assert EchoTool()(text="hi") == "hi"

    def test_schema_shape(self):
        from tools.base_tool import BaseTool
        schema = BaseTool().schema()
        assert "name" in schema and "parameters" in schema


class TestOpenAITool:
    def test_validate_missing_prompt_raises(self):
        from tools.openai_tool import OpenAITool
        tool = OpenAITool(api_key="key")
        with pytest.raises(ValueError):
            tool.validate()

    def test_validate_missing_key_raises(self):
        from tools.openai_tool import OpenAITool
        tool = OpenAITool(api_key="")
        with pytest.raises(RuntimeError):
            tool.validate(prompt="hello")

    def test_schema(self):
        from tools.openai_tool import OpenAITool
        s = OpenAITool().schema()
        assert "prompt" in s["parameters"]["properties"]


class TestEmailTool:
    def test_validate_missing_to_raises(self):
        from tools.email_tool import EmailTool
        with pytest.raises(ValueError):
            EmailTool().validate(subject="hi", body="body")

    def test_execute_no_config_raises(self):
        from tools.email_tool import EmailTool
        tool = EmailTool()
        with pytest.raises(RuntimeError):
            tool.execute(to="a@b.com", subject="hi", body="test")

    def test_schema(self):
        from tools.email_tool import EmailTool
        s = EmailTool().schema()
        assert "to" in s["parameters"]["properties"]
        assert "to" in s["parameters"]["required"]


# ═══════════════════════════════════════════════════════════════════════════════
# Orchestration
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiAgentOrchestrator:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _make_msg(self, content="hi", session_id="s1", source="web"):
        return type("Msg", (), {"content": content, "session_id": session_id, "source": source})()

    def setup_method(self):
        import gateway.router as r
        r._registry.clear()
        r._fallback = None

    def test_process_message_uses_default_agent(self):
        from orchestration.multi_agent_orchestrator import MultiAgentOrchestrator
        delivered = []

        class FakeMessenger:
            def send(self, resp, source, session_id):
                delivered.append(resp)

        orch = MultiAgentOrchestrator(messenger=FakeMessenger())
        self._run(orch.process_message(self._make_msg()))
        assert len(delivered) == 1
        assert isinstance(delivered[0], str)


class TestCronScheduler:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_add_and_run_one_tick(self):
        from orchestration.cron_scheduler import CronScheduler
        called = []

        scheduler = CronScheduler(tick=0.01)
        scheduler.add_job("test_job", lambda: called.append(1), interval=0)

        async def run_briefly():
            task = asyncio.create_task(scheduler.run())
            await asyncio.sleep(0.05)
            scheduler.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._run(run_briefly())
        assert len(called) > 0

    def test_remove_job(self):
        from orchestration.cron_scheduler import CronScheduler
        scheduler = CronScheduler()
        scheduler.add_job("j1", lambda: None, interval=60)
        scheduler.remove_job("j1")
        assert "j1" not in scheduler._jobs


class TestHeartbeat:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_heartbeat_calls_proactive_tasks(self):
        from orchestration.heartbeat import heartbeat_task
        ticked = []

        class FakeAgent:
            name = "fake"

            def perform_proactive_tasks(self):
                ticked.append(1)

        async def run_one_tick():
            task = asyncio.create_task(heartbeat_task([FakeAgent()], interval=0.01))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._run(run_one_tick())
        assert len(ticked) > 0
