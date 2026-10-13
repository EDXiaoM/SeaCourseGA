"""Shared pytest setup of the course project. 课程设计测试的公共设置。

pytest loads this file automatically before the test modules in ``tests/``.
It makes the in-repository package ``maritime_route`` importable from
``src/`` without installing it.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import ``maritime_route`` from src/ without installing the package.
# 无需安装即可从 src 目录导入。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
