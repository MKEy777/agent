# 文件说明：本文件属于 命令行层。
# 主要职责：实现 main 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""OpenClaw CLI — main entry point."""

import typer

from openclaw.cli.backup import backup_app
from openclaw.cli.config_cmd import config_app
from openclaw.cli.doctor import doctor_app
from openclaw.cli.gateway import gateway_app
from openclaw.cli.logs import logs_app
from openclaw.cli.models import models_app
from openclaw.cli.onboard import onboard_app
from openclaw.cli.sessions import sessions_app
from openclaw.cli.setup import setup_app
from openclaw.cli.status import status_app

app = typer.Typer(name="openclaw", help="OpenClaw — Multi-channel AI Gateway")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("OpenClaw v0.1.0 — use --help for commands")


app.add_typer(gateway_app, name="gateway", help="Gateway server management")
app.add_typer(config_app, name="config", help="Configuration management")
app.add_typer(sessions_app, name="sessions", help="Session management")
app.add_typer(models_app, name="models", help="Model information")
app.add_typer(doctor_app, name="doctor", help="Diagnostics")
app.add_typer(status_app, name="status", help="Status information")
app.add_typer(setup_app, name="setup", help="Channel setup wizard")
app.add_typer(onboard_app, name="onboard", help="First-time setup")
app.add_typer(logs_app, name="logs", help="Log management")
app.add_typer(backup_app, name="backup", help="Backup and restore")


if __name__ == "__main__":
    app()
