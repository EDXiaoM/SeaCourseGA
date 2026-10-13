# Sea Course GA — 课程设计

**基于遗传算法、在开阔海域点上寻找海船最优航线的应用程序**

**俄文版 — [README_ru.md](README_ru.md)** · English — [README.md](README.md)

课程设计 · Li Haoran（Ли Хаожань），ИИ-2025 班 · 布列斯特国立技术大学 智能信息技术教研室 · 指导老师 А.А. Козинский · 2026 · 文档编号 `KP.ИИ2025.250978-01 81 00`

> 本仓库只包含**课程设计**。同一作者的毕业设计在另一个仓库：<https://github.com/EDXiaoM/MaritimeRouteAI>。

## 材料

| 材料 | 文件 |
|---|---|
| 说明书（PDF） | [`docs/note/KP_explanatory_note_Li_Haoran.pdf`](docs/note/KP_explanatory_note_Li_Haoran.pdf) |
| 说明书（Word） | [`docs/note/KP_explanatory_note_Li_Haoran.docx`](docs/note/KP_explanatory_note_Li_Haoran.docx) |
| 图纸（5 张 A4） | [`docs/note/KP_graphic_material_5_sheets.pdf`](docs/note/KP_graphic_material_5_sheets.pdf) |
| 任务书（俄文） | [`docs/note/Assignment_course_ru.pdf`](docs/note/Assignment_course_ru.pdf) |
| **用户手册**（说明书附录 A） | [`docs/User_Guide_SeaCourseGA.pdf`](docs/User_Guide_SeaCourseGA.pdf) |
| 程序代码 | [`src/`](src)、[`scripts/`](scripts)、[`tests/`](tests) |
| 实验结果、插图、截图 | [`docs/course/`](docs/course) |
| 数据集（152,838 个点，压缩包 7 MB） | [Release v1.0](https://github.com/EDXiaoM/SeaCourseGA/releases/tag/v1.0) 中的 `merged_json_v1_course.zip` |

## 运行

```bat
git clone https://github.com/EDXiaoM/SeaCourseGA.git
cd SeaCourseGA
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-course.txt
python scripts/run_desktop.py
```

从 Release 下载 `merged_json_v1_course.zip`，把 `merged.json` 解压到 `data/raw/`，程序启动时会自动打开。测试：`python -m pytest`（34 个）。完整说明见英文版 [README.md](README.md)。
