# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 config load 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Contract tests for config loading — verify fixture compatibility."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from openclaw.config.loader import load_config
from openclaw.contracts.config.types_openclaw import OpenClawConfig
from openclaw.core.env import load_default_env_files, parse_env_assignment

if TYPE_CHECKING:
    import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


class TestConfigLoad:
    def test_load_real_config(self) -> None:
        data = json.loads((FIXTURES_DIR / "real_config.json").read_text())
        config = OpenClawConfig.model_validate(data)
        assert config.gateway is not None
        assert config.gateway.port == 18789
        assert config.gateway.auth is not None
        assert config.gateway.auth.mode == "token"
        assert config.channels is not None
        assert config.channels.feishu is not None
        assert config.channels.feishu.enabled is True
        assert config.logging is not None
        assert config.logging.level == "info"

    def test_round_trip(self) -> None:
        data = json.loads((FIXTURES_DIR / "real_config.json").read_text())
        config = OpenClawConfig.model_validate(data)
        dumped = json.loads(config.model_dump_json(exclude_none=True, by_alias=True))
        # Key fields survive round-trip
        assert dumped["gateway"]["port"] == 18789
        assert dumped["gateway"]["auth"]["mode"] == "token"
        assert dumped["channels"]["feishu"]["enabled"] is True

    def test_empty_config(self) -> None:
        config = OpenClawConfig.model_validate({})
        assert config.gateway is None
        assert config.channels is None

    def test_unknown_fields_allowed(self) -> None:
        config = OpenClawConfig.model_validate({"futureField": "value"})
        assert config.model_extra is not None

    def test_load_config_uses_openclaw_config_path(self, tmp_path: Path) -> None:
        config_path = tmp_path / "openclaw.json"
        config_path.write_text('{"gateway": {"port": 19001}}\n', encoding="utf-8")

        config = load_config(env={"OPENCLAW_CONFIG_PATH": str(config_path)})

        assert config.gateway is not None
        assert config.gateway.port == 19001

    def test_load_config_uses_home_default_path(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".openclaw"
        state_dir.mkdir()
        (state_dir / "openclaw.json").write_text(
            '{"channels": {"feishu": {"enabled": true}}}\n',
            encoding="utf-8",
        )

        config = load_config(env={"HOME": str(tmp_path)})

        assert config.channels is not None
        assert config.channels.feishu is not None
        assert config.channels.feishu.enabled is True

    def test_parse_env_assignment_supports_export_and_quotes(self) -> None:
        assert parse_env_assignment('export FEISHU_APP_ID="cli_xxx"') == (
            "FEISHU_APP_ID",
            "cli_xxx",
        )

    def test_load_default_env_files_prefers_dotenv(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("FEISHU_APP_SECRET", raising=False)
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        (tmp_path / ".env").write_text(
            "FEISHU_APP_SECRET=from_env\nDASHSCOPE_API_KEY=dashscope\n",
            encoding="utf-8",
        )
        (tmp_path / "process.md").write_text(
            "export FEISHU_APP_SECRET=from_process\n",
            encoding="utf-8",
        )

        loaded = load_default_env_files(tmp_path)

        assert loaded == [tmp_path / ".env"]
        assert os.environ["FEISHU_APP_SECRET"] == "from_env"
        assert os.environ["DASHSCOPE_API_KEY"] == "dashscope"
