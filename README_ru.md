# Sea Course GA — курсовой проект

**Разработка приложения для поиска оптимального курса морского судна по точкам
открытого моря на основе генетического алгоритма**

English — [README.md](README.md) · 中文 — [README_zh.md](README_zh.md)

Курсовой проект · Ли Хаожань (Li Haoran), группа ИИ-2025 · Брестский
государственный технический университет, кафедра интеллектуальных
информационных технологий · руководитель А.А. Козинский · 2026 · обозначение
документа `KP.ИИ2025.250978-01 81 00`

> В этом репозитории размещён только **курсовой проект**. Дипломный проект
> автора находится в отдельном репозитории:
> <https://github.com/EDXiaoM/MaritimeRouteAI>.

## Материалы

| Материал | Файл |
|---|---|
| Пояснительная записка (PDF) | [`docs/note/KP_explanatory_note_Li_Haoran.pdf`](docs/note/KP_explanatory_note_Li_Haoran.pdf) |
| Пояснительная записка (Word) | [`docs/note/KP_explanatory_note_Li_Haoran.docx`](docs/note/KP_explanatory_note_Li_Haoran.docx) |
| Графический материал, 5 листов A4 | [`docs/note/KP_graphic_material_5_sheets.pdf`](docs/note/KP_graphic_material_5_sheets.pdf) |
| Задание на курсовой проект | [`docs/note/Assignment_course_ru.pdf`](docs/note/Assignment_course_ru.pdf) |
| **Руководство пользователя** (приложение A записки) | [`docs/User_Guide_SeaCourseGA.pdf`](docs/User_Guide_SeaCourseGA.pdf) |
| Текст программы | [`src/`](src), [`scripts/`](scripts), [`tests/`](tests) |
| Результаты экспериментов, рисунки, снимки экрана | [`docs/course/`](docs/course) |
| Набор данных (152 838 точек, архив 7 МБ) | `merged_json_v1_course.zip` в [релизе v1.0](https://github.com/EDXiaoM/SeaCourseGA/releases/tag/v1.0) |

Пояснительная записка, руководство пользователя и комментарии в программе
написаны на английском языке.

## Назначение программы

Настольное приложение (PyQt5) загружает размеченный набор данных (точки WGS-84
четырёх классов), удаляет точки, класс которых противоречит глубине, строит
навигационный граф на точках акватории, ищет курс судна **генетическим
алгоритмом**, а оптимальный курс — алгоритмами **Дейкстры** и **A\*** на том же
графе, показывает три маршрута на карте, строит график сходимости генетического
алгоритма и сохраняет результаты (карта, график сходимости, маршруты в
GeoJSON/CSV, таблица сравнения, журнал параметров).

## Результаты (раздел 3.4 записки)

| Результат | Значение |
|---|---|
| Набор данных после очистки | 147 763 из 152 838 точек (удалено 5 075 точек с противоречием класса и глубины) |
| Тестовые рейсы | 7 (Чёрное море, Южно-Китайское море, Южная Африка, Ормузский пролив, Карибское море) |
| Алгоритмы Дейкстры и A\* | одинаковая оптимальная стоимость на всех рейсах; A\* раскрывает в среднем в 1,97 раза меньше вершин |
| Генетический алгоритм | судоходный маршрут во всех 70 запусках (по 10 на рейс); в 57 запусках отклонение от оптимума не более 1 %; среднее отклонение 0,90 % |

## Состав программы

| Путь | Содержание |
|---|---|
| `src/maritime_route/pointgraph/` | загрузка данных, граф, модель стоимости, Дейкстра/A\*, генетический алгоритм, сеанс, экспорт |
| `src/maritime_route/desktop/` | главное окно PyQt5 и фоновые потоки |
| `src/maritime_route/data/`, `routing/geodesy.py`, `config.py` | загрузчик данных, правило очистки и сферическая геометрия, общие с дипломным проектом |
| `scripts/run_desktop.py` | запуск приложения |
| `scripts/course_experiments.py` | все эксперименты раздела 3.4 → `docs/course/results.json`, рисунки |
| `scripts/course_extra_figures.py`, `course_diagrams.py` | рисунки разделов 2 и 3.4 |
| `scripts/course_screenshots.py` | снимки экрана приложения (работает без дисплея) |
| `scripts/course_sheets.py` | пять листов графического материала A4 → `docs/course/sheets/` |
| `tests/` | 34 автоматических теста |
| `requirements-course.txt` | зависимости |

## Установка и запуск

Требуется Python 3.10 или новее (Ubuntu 20.04: дополнительно установить
`python3.10`, например из PPA deadsnakes; Fedora 38+ и Windows: стандартный
установщик Python).

Windows:

```bat
git clone https://github.com/EDXiaoM/SeaCourseGA.git
cd SeaCourseGA
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-course.txt
python scripts/run_desktop.py
```

Linux:

```bash
git clone https://github.com/EDXiaoM/SeaCourseGA.git
cd SeaCourseGA
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-course.txt
python scripts/run_desktop.py
```

Скачайте `merged_json_v1_course.zip` из
[релиза](https://github.com/EDXiaoM/SeaCourseGA/releases/tag/v1.0) и распакуйте
`merged.json` в папку `data/raw/` — приложение откроет его автоматически. Любой
другой файл открывается через меню *File → Open dataset…*.

Если в Ubuntu Qt сообщает *Could not load the Qt platform plugin "xcb"*,
установите пакет: `sudo apt install libxcb-xinerama0`.

## Воспроизведение результатов записки

```bash
python -m pytest                            # 34 теста
python scripts/course_experiments.py        # около 20 минут, записывает docs/course/results.json
python scripts/course_extra_figures.py
python scripts/course_diagrams.py
python scripts/course_sheets.py
```

Генетический алгоритм использует фиксированное начальное значение генератора
случайных чисел, поэтому маршруты и стоимости воспроизводятся точно; время
работы зависит от компьютера.
