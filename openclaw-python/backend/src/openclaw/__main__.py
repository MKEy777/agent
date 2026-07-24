# 文件说明：本文件属于 OpenClaw 源码层。
# 主要职责：提供 python -m 模块入口。
# 阅读提示：承载项目 Python 模块。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Allow running as: python -m openclaw"""

from openclaw.cli.main import app

app()
