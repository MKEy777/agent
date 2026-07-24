# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 session store 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Contract tests for session store — verify fixture compatibility."""

from __future__ import annotations

import json
from pathlib import Path

from openclaw.contracts.session.entry import SessionEntry
from openclaw.contracts.session.transcript import TranscriptLine

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


class TestSessionStore:
    def test_load_real_sessions(self) -> None:
        data = json.loads((FIXTURES_DIR / "real_sessions.json").read_text())
        store = {k: SessionEntry.model_validate(v) for k, v in data.items()}
        assert "main" in store
        assert store["main"].session_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert store["main"].channel == "webchat"
        assert store["main"].status == "done"

    def test_feishu_session(self) -> None:
        data = json.loads((FIXTURES_DIR / "real_sessions.json").read_text())
        store = {k: SessionEntry.model_validate(v) for k, v in data.items()}
        key = "dm:feishu:ou_abcdef123456"
        assert key in store
        assert store[key].channel == "feishu"
        assert store[key].last_channel == "feishu"

    def test_round_trip(self) -> None:
        data = json.loads((FIXTURES_DIR / "real_sessions.json").read_text())
        for _key, raw in data.items():
            entry = SessionEntry.model_validate(raw)
            dumped = json.loads(entry.model_dump_json(exclude_none=True, by_alias=True))
            assert dumped["sessionId"] == raw["sessionId"]
            assert dumped["updatedAt"] == raw["updatedAt"]


class TestTranscript:
    def test_load_real_transcript(self) -> None:
        lines: list[TranscriptLine] = []
        for raw_line in (FIXTURES_DIR / "real_transcript.jsonl").read_text().strip().split("\n"):
            lines.append(TranscriptLine.model_validate_json(raw_line))
        assert len(lines) == 5
        assert lines[0].role == "system"
        assert lines[1].role == "user"
        assert lines[2].role == "assistant"
        assert lines[2].usage is not None


class TestPluginManifest:
    def test_load_anthropic_manifest(self) -> None:
        from openclaw.contracts.plugin.manifest import PluginManifest

        data = json.loads((FIXTURES_DIR / "plugin_manifests" / "anthropic.json").read_text())
        manifest = PluginManifest.model_validate(data)
        assert manifest.id == "anthropic"
        assert manifest.providers is not None
        assert "anthropic" in manifest.providers

    def test_load_feishu_manifest(self) -> None:
        from openclaw.contracts.plugin.manifest import PluginManifest

        path = FIXTURES_DIR / "plugin_manifests" / "feishu.json"
        if path.exists():
            data = json.loads(path.read_text())
            manifest = PluginManifest.model_validate(data)
            assert manifest.id is not None
