"""Окно приложения: ввод исходных данных, расчёт, таблицы, графики и отчёт в Excel."""

from __future__ import annotations

import os
import subprocess
import sys

# PySide6 подключается раньше matplotlib: так библиотека графиков использует именно его,
# а не другую установленную в системе сборку Qt.
os.environ.setdefault("QT_API", "pyside6")
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QSpinBox, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QTextBrowser,
    QVBoxLayout, QWidget,
)

from .excel_report import save_workbook
from .lfsr import LFSR, POLYNOMIALS, polynomial_text
from .model import Parameters, SimulationResult, collect_trials, simulate

ACCENT = "#1f6feb"
DARK = "#16233a"
LIGHT = "#f4f7fb"
GOOD = "#1a7f37"

STYLE = f"""
QMainWindow, QWidget#Root {{ background: {LIGHT}; }}
QLabel#Title {{ color: white; font-size: 19px; font-weight: 600; }}
QLabel#Subtitle {{ color: #c7d6ee; font-size: 12px; }}
QFrame#Header {{ background: {DARK}; border: none; }}
QGroupBox {{
    background: white; border: 1px solid #d7e0ee; border-radius: 10px;
    margin-top: 14px; padding: 10px 8px 8px 8px; font-weight: 600; color: #223;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
QPushButton {{
    background: {ACCENT}; color: white; border: none; border-radius: 8px;
    padding: 9px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: #3b82f6; }}
QPushButton:disabled {{ background: #9db6d8; }}
QPushButton#Secondary {{ background: white; color: {ACCENT}; border: 1px solid {ACCENT}; }}
QPushButton#Secondary:hover {{ background: #eaf2ff; }}
QTableWidget {{
    background: white; border: 1px solid #d7e0ee; border-radius: 8px;
    gridline-color: #e6ecf5; selection-background-color: #dbeafe; selection-color: #16233a;
}}
QHeaderView::section {{
    background: #eef3fa; color: #223; border: none; border-right: 1px solid #dfe7f2;
    border-bottom: 1px solid #dfe7f2; padding: 7px; font-weight: 600;
}}
QTabWidget::pane {{ border: 1px solid #d7e0ee; border-radius: 10px; background: white; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: #4a5a72; padding: 9px 16px; margin-right: 4px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600;
}}
QTabBar::tab:selected {{ background: white; color: {ACCENT}; border: 1px solid #d7e0ee; border-bottom: 1px solid white; }}
QFrame#Card {{ background: white; border: 1px solid #d7e0ee; border-radius: 10px; }}
QLabel#CardValue {{ font-size: 20px; font-weight: 700; color: {DARK}; }}
QLabel#CardName {{ color: #5b6b83; font-size: 12px; }}
QLabel#CardHint {{ color: {GOOD}; font-size: 12px; font-weight: 600; }}
QTextBrowser {{ background: white; border: 1px solid #d7e0ee; border-radius: 8px; padding: 10px; }}
QStatusBar {{ background: white; color: #4a5a72; }}
"""


class Worker(QThread):
    """Расчёт выполняется в отдельном потоке, чтобы окно не подвисало."""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, params: Parameters, example_percent: int) -> None:
        super().__init__()
        self.params = params
        self.example_percent = example_percent

    def run(self) -> None:
        try:
            self.done.emit(simulate(self.params, self.example_percent))
        except Exception as error:  # показывается пользователю в окне сообщения
            self.failed.emit(str(error))


def number(value: float, digits: int = 2) -> str:
    """Число с запятой в качестве десятичного разделителя — как принято в русском тексте."""
    return f"{value:.{digits}f}".replace(".", ",")


def card(name: str, value: str = "—", hint: str = "") -> tuple[QFrame, QLabel, QLabel]:
    """Карточка с крупным числом: название, значение, подпись."""
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 10, 14, 10)
    title = QLabel(name)
    title.setObjectName("CardName")
    value_label = QLabel(value)
    value_label.setObjectName("CardValue")
    hint_label = QLabel(hint)
    hint_label.setObjectName("CardHint")
    layout.addWidget(title)
    layout.addWidget(value_label)
    layout.addWidget(hint_label)
    return frame, value_label, hint_label


class MainWindow(QMainWindow):
    """Главное окно лабораторной работы."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Метод Монте-Карло — входной контроль резисторов (вариант 3)")
        self.resize(1320, 840)
        self.result: SimulationResult | None = None
        self.worker: Worker | None = None
        self._build()
        self.run_simulation()

    # ---------- построение интерфейса ----------

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._header())

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(16, 14, 16, 10)
        body_layout.setSpacing(14)
        body_layout.addWidget(self._side_panel(), 0)
        body_layout.addWidget(self._tabs(), 1)
        outer.addWidget(body, 1)
        self.statusBar().showMessage("Готово к расчёту")

    def _header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Header")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(2)
        title = QLabel("Лабораторная работа № 1. Принятие решений на основе метода Монте-Карло")
        title.setObjectName("Title")
        subtitle = QLabel(
            "Задача: найти долю резисторов, которую выгодно подвергать входному контролю. "
            "Псевдослучайные числа — сдвиговый регистр (LFSR), вариант 3, полином № 9."
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return frame

    def _side_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(330)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        data_box = QGroupBox("Исходные данные (вариант 3)")
        form = QFormLayout(data_box)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(8)

        self.defect = QDoubleSpinBox(maximum=100.0, decimals=1, singleStep=1.0, suffix=" %")
        self.defect.setValue(10.0)
        self.control_cost = QDoubleSpinBox(maximum=10_000.0, decimals=2, suffix=" руб.")
        self.control_cost.setValue(4.0)
        self.fitting_cost = QDoubleSpinBox(maximum=10_000.0, decimals=2, suffix=" руб.")
        self.fitting_cost.setValue(60.0)
        self.replace_cost = QDoubleSpinBox(maximum=10_000.0, decimals=2, suffix=" руб.")
        self.replace_cost.setValue(140.0)
        form.addRow("A — негодных резисторов", self.defect)
        form.addRow("B — контроль одного", self.control_cost)
        form.addRow("C — подгонка", self.fitting_cost)
        form.addRow("D — замена в изделии", self.replace_cost)

        calc_box = QGroupBox("Настройки расчёта")
        calc_form = QFormLayout(calc_box)
        calc_form.setSpacing(8)
        self.trials = QSpinBox(minimum=100, maximum=1_000_000, singleStep=1000)
        self.trials.setValue(10_000)
        self.trials.setGroupSeparatorShown(True)
        self.step = QSpinBox(minimum=1, maximum=25, suffix=" %")
        self.step.setValue(5)
        self.polynomial = QComboBox()
        for number in sorted(POLYNOMIALS):
            self.polynomial.addItem(f"№ {number}", number)
        self.polynomial.setCurrentIndex(sorted(POLYNOMIALS).index(9))
        self.seed = QSpinBox(minimum=1, maximum=2_147_483_647)
        self.seed.setValue(0x2025_5445)
        self.seed.setGroupSeparatorShown(True)
        self.example_percent = QSpinBox(minimum=0, maximum=100, singleStep=5, suffix=" %")
        self.example_percent.setValue(50)
        calc_form.addRow("Испытаний (резисторов)", self.trials)
        calc_form.addRow("Шаг доли контроля", self.step)
        calc_form.addRow("Полином LFSR", self.polynomial)
        calc_form.addRow("Начальное состояние", self.seed)
        calc_form.addRow("Доля для примера", self.example_percent)

        self.run_button = QPushButton("Рассчитать")
        self.run_button.clicked.connect(self.run_simulation)
        self.excel_button = QPushButton("Отчёт в Excel")
        self.excel_button.setObjectName("Secondary")
        self.excel_button.clicked.connect(self.save_excel)
        self.chart_button = QPushButton("Сохранить график")
        self.chart_button.setObjectName("Secondary")
        self.chart_button.clicked.connect(self.save_chart)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)

        layout.addWidget(data_box)
        layout.addWidget(calc_box)
        layout.addWidget(self.run_button)
        layout.addWidget(self.excel_button)
        layout.addWidget(self.chart_button)
        layout.addWidget(self.progress)
        layout.addStretch(1)
        return panel

    def _tabs(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.card_best, self.card_best_value, self.card_best_hint = card("Лучшая доля контроля")
        self.card_cost, self.card_cost_value, self.card_cost_hint = card("Затраты при лучшей доле")
        self.card_save, self.card_save_value, self.card_save_hint = card("Экономия против худшего варианта")
        self.card_theory, self.card_theory_value, self.card_theory_hint = card("Теоретическая проверка")
        for widget in (self.card_best, self.card_cost, self.card_save, self.card_theory):
            cards.addWidget(widget)
        layout.addLayout(cards)

        self.tabs = QTabWidget()
        self.table_percent = self._table(
            ["Доля\nконтроля, %", "Проверено,\nшт.", "Подгонок,\nшт.", "Замен,\nшт.",
             "Контроль,\nруб.", "Подгонка,\nруб.", "Замена,\nруб.",
             "Итого,\nруб.", "Теория,\nруб.", "Отклонение,\n%"]
        )
        self.tabs.addTab(self._wrap(self.table_percent), "Результаты по долям")

        self.figure = Figure(figsize=(7, 4.4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.tabs.addTab(self._wrap(self.canvas), "График затрат")

        self.table_trials = self._table(
            ["Номер\nиспытания", "R1", "Контроль", "R2", "Нужна\nподгонка", "Затраты,\nруб.", "Общие\nзатраты, руб.", "Событие"]
        )
        # последний столбец растягивается по содержимому, чтобы название события было видно целиком
        self.table_trials.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.tabs.addTab(self._wrap(self.table_trials), "Испытания")

        generator_tab = QWidget()
        gen_layout = QVBoxLayout(generator_tab)
        gen_layout.setContentsMargins(10, 10, 10, 10)
        self.generator_figure = Figure(figsize=(7, 3.4), dpi=100)
        self.generator_canvas = FigureCanvas(self.generator_figure)
        self.generator_info = QLabel()
        self.generator_info.setWordWrap(True)
        gen_layout.addWidget(self.generator_canvas, 1)
        gen_layout.addWidget(self.generator_info)
        self.tabs.addTab(generator_tab, "Генератор ПСЧ")

        self.help_view = QTextBrowser()
        self.help_view.setHtml(HELP_HTML)
        self.tabs.addTab(self._wrap(self.help_view), "Как считается")

        layout.addWidget(self.tabs, 1)
        return container

    @staticmethod
    def _wrap(widget: QWidget) -> QWidget:
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(widget)
        return holder

    @staticmethod
    def _table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    # ---------- расчёт ----------

    def parameters(self) -> Parameters:
        """Считывание введённых значений в параметры расчёта."""
        return Parameters(
            defect_percent=self.defect.value(),
            cost_control=self.control_cost.value(),
            cost_fitting=self.fitting_cost.value(),
            cost_replace=self.replace_cost.value(),
            trials=self.trials.value(),
            percent_step=self.step.value(),
            polynomial=self.polynomial.currentData(),
            seed=self.seed.value(),
        )

    def run_simulation(self) -> None:
        params = self.parameters()
        self.run_button.setEnabled(False)
        self.progress.setVisible(True)
        self.statusBar().showMessage("Идёт расчёт…")
        self.worker = Worker(params, self.example_percent.value())
        self.worker.done.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.start()

    def show_error(self, message: str) -> None:
        self.progress.setVisible(False)
        self.run_button.setEnabled(True)
        QMessageBox.critical(self, "Ошибка расчёта", message)

    def show_result(self, result: SimulationResult) -> None:
        self.result = result
        self.progress.setVisible(False)
        self.run_button.setEnabled(True)
        self._fill_percent_table(result)
        self._fill_trials_table(result)
        self._draw_chart(result)
        self._draw_generator(result)
        self._fill_cards(result)
        self.statusBar().showMessage(
            f"Расчёт выполнен: {result.parameters.describe()}. "
            f"Лучшая доля контроля — {result.best.percent} %."
        )

    def _fill_cards(self, result: SimulationResult) -> None:
        best = result.best
        self.card_best_value.setText(f"{best.percent} %")
        self.card_best_hint.setText(f"из {len(result.rows)} рассмотренных вариантов")
        self.card_cost_value.setText(f"{best.total_cost:,.0f}".replace(",", " "))
        self.card_cost_hint.setText(f"на {result.parameters.trials:,} резисторов".replace(",", " "))
        self.card_save_value.setText(f"{result.saving():,.0f}".replace(",", " "))
        self.card_save_hint.setText(f"худший вариант — {result.worst.percent} %")
        self.card_theory_value.setText(f"{result.best_expected.percent} %")
        same = result.best.percent == result.best_expected.percent
        self.card_theory_hint.setText("совпадает с моделью" if same else "отличается от модели")
        self.card_theory_hint.setStyleSheet("" if same else "color: #b54708;")

    def _fill_percent_table(self, result: SimulationResult) -> None:
        table = self.table_percent
        table.setRowCount(len(result.rows))
        best = result.best
        for row_index, row in enumerate(result.rows):
            values = [
                f"{row.percent}",
                f"{row.controlled}",
                f"{row.fitted}",
                f"{row.replaced}",
                f"{row.control_cost:,.0f}".replace(",", " "),
                f"{row.fitting_cost:,.0f}".replace(",", " "),
                f"{row.replace_cost:,.0f}".replace(",", " "),
                f"{row.total_cost:,.0f}".replace(",", " "),
                f"{row.expected_cost:,.0f}".replace(",", " "),
                ("+" if row.deviation >= 0 else "") + number(row.deviation),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                if row is best:
                    item.setBackground(QColor("#e6f4ea"))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                table.setItem(row_index, column, item)

    def _fill_trials_table(self, result: SimulationResult) -> None:
        table = self.table_trials
        trials = result.trials_example
        table.setRowCount(len(trials))
        for row_index, trial in enumerate(trials):
            values = [
                str(trial.number),
                number(trial.r1, 4),
                "да" if trial.controlled else "нет",
                number(trial.r2, 4),
                "да" if trial.defective else "нет",
                f"{trial.cost:.0f}",
                f"{trial.total:,.0f}".replace(",", " "),
                trial.event,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                if trial.cost:
                    item.setBackground(QColor("#fff4e5"))
                table.setItem(row_index, column, item)
        self.tabs.setTabText(2, f"Испытания (доля {result.example_percent} %)")

    def _draw_chart(self, result: SimulationResult) -> None:
        self.figure.clear()
        axes = self.figure.add_subplot(111)
        percents = [row.percent for row in result.rows]
        totals = [row.total_cost for row in result.rows]
        theory = [row.expected_cost for row in result.rows]
        axes.plot(percents, totals, marker="o", color=ACCENT, linewidth=2, label="Моделирование")
        axes.plot(percents, theory, linestyle="--", color="#8a94a6", linewidth=1.6, label="Теоретическая формула")
        best = result.best
        axes.scatter([best.percent], [best.total_cost], s=140, zorder=5, color="#1a7f37")
        axes.annotate(
            f"минимум: {best.percent} %",
            xy=(best.percent, best.total_cost),
            xytext=(10, 18),
            textcoords="offset points",
            color="#1a7f37",
            fontweight="bold",
        )
        axes.set_xlabel("Доля резисторов, проходящих входной контроль, %")
        axes.set_ylabel("Общие затраты, руб.")
        axes.set_title(f"Затраты на {result.parameters.trials:,} резисторов".replace(",", " "))
        axes.grid(alpha=0.3)
        axes.legend()
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _draw_generator(self, result: SimulationResult) -> None:
        numbers = [value for pair in result.numbers for value in pair]
        self.generator_figure.clear()
        left = self.generator_figure.add_subplot(121)
        left.hist(numbers, bins=20, range=(0, 1), color=ACCENT, alpha=0.85, edgecolor="white")
        left.axhline(len(numbers) / 20, color="#d1495b", linestyle="--", linewidth=1.4, label="ожидаемая частота")
        left.set_title("Распределение псевдослучайных чисел")
        left.set_xlabel("значение")
        left.set_ylabel("количество")
        left.legend(fontsize=8)

        right = self.generator_figure.add_subplot(122)
        pairs = result.numbers[:2000]
        right.scatter([p[0] for p in pairs], [p[1] for p in pairs], s=4, alpha=0.5, color="#1a7f37")
        right.set_title("Пары чисел (R1, R2)")
        right.set_xlabel("R1")
        right.set_ylabel("R2")
        self.generator_figure.tight_layout()
        self.generator_canvas.draw_idle()

        average = sum(numbers) / len(numbers)
        variance = sum((x - average) ** 2 for x in numbers) / len(numbers)
        counts = [0] * 10
        for value in numbers:
            counts[min(9, int(value * 10))] += 1
        expected = len(numbers) / 10
        chi2 = sum((count - expected) ** 2 / expected for count in counts)
        self.generator_info.setText(
            f"<b>Полином № {result.parameters.polynomial}:</b> {polynomial_text(result.parameters.polynomial)}<br>"
            f"Чисел получено: {len(numbers):,}".replace(",", " ") +
            f" &nbsp;•&nbsp; среднее: <b>{number(average, 4)}</b> (ожидается 0,5)"
            f" &nbsp;•&nbsp; дисперсия: <b>{number(variance, 4)}</b> (ожидается 0,0833)<br>"
            f"Критерий согласия χ² по десяти интервалам: <b>{number(chi2)}</b> "
            f"(граница для уровня значимости 0,05 и девяти степеней свободы — 16,92; "
            f"{'числа равномерны' if chi2 < 16.92 else 'равномерность под вопросом'})."
        )

    # ---------- сохранение ----------

    def save_excel(self) -> None:
        if not self.result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", "Проверка_ЛР1_Монте-Карло.xlsx", "Книга Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            save_workbook(self.result, path)
        except PermissionError:
            QMessageBox.warning(self, "Файл занят", "Закройте файл в Excel и повторите сохранение.")
            return
        self.statusBar().showMessage(f"Отчёт сохранён: {path}")
        if QMessageBox.question(self, "Отчёт готов", "Открыть файл в Excel?") == QMessageBox.Yes:
            self._open_file(path)

    def save_chart(self) -> None:
        if not self.result:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить график", "Затраты.png", "Изображение (*.png)")
        if path:
            self.figure.savefig(path, dpi=150, facecolor="white")
            self.statusBar().showMessage(f"График сохранён: {path}")

    @staticmethod
    def _open_file(path: str) -> None:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606 — открытие файла средствами системы
        else:
            subprocess.Popen(["xdg-open", path])


HELP_HTML = """
<h3>Что делает программа</h3>
<p>Программа моделирует входной контроль резисторов и подбирает долю резисторов,
которую выгодно проверять. Для каждой доли от 0 до 100 % разыгрывается заданное
количество испытаний, и подсчитываются суммарные затраты.</p>

<h3>Одно испытание</h3>
<ol>
<li>Берутся два псевдослучайных числа <b>R1</b> и <b>R2</b> из диапазона (0; 1).</li>
<li>Если <b>R1 &lt; P</b> (P — доля контроля), резистор попал на контроль: к затратам добавляется <b>B</b>.
    Если при этом <b>R2 &lt; A</b>, резистор негодный и его подгоняют: добавляется <b>C</b>.</li>
<li>Если резистор не попал на контроль, а <b>R2 &lt; A</b>, брак обнаружится в готовом изделии:
    добавляется <b>D</b>.</li>
</ol>

<h3>Откуда берутся псевдослучайные числа</h3>
<p>Числа даёт сдвиговый регистр с линейной обратной связью. Регистр из 32 ячеек на каждом такте
сдвигается, а в первую ячейку записывается сумма по модулю 2 разрядов, заданных полиномом варианта.
Каждое число собирается из 32 подряд идущих выходных битов, поэтому соседние числа не связаны.</p>

<h3>Проверка результата</h3>
<p>Для каждой доли контроля рассчитывается теоретическое значение затрат:</p>
<p style="text-align:center"><b>Затраты = n · ( P·B + P·A·C + (1 − P)·A·D )</b></p>
<p>Моделирование должно давать близкие числа — расхождение видно в таблице результатов.
Кнопка «Отчёт в Excel» выгружает те же псевдослучайные числа и пересчитывает затраты
формулами Excel: это независимая проверка расчёта.</p>

<h3>Как читать вывод</h3>
<p>Лучшей считается доля контроля с наименьшими общими затратами. Если затраты убывают
до самого конца, выгодно проверять все резисторы; если растут — контроль не окупается.</p>
"""


def run_application() -> int:
    """Запуск приложения."""
    application = QApplication(sys.argv)
    application.setStyleSheet(STYLE)
    application.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    return application.exec()
