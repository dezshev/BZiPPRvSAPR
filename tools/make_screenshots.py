"""Снимки окна приложения для README.

Скрипт запускает окно, дожидается окончания расчёта и сохраняет каждую вкладку
в файл docs/img/app_*.png. Запуск: python tools/make_screenshots.py
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

from montecarlo.ui import STYLE, MainWindow  # noqa: E402

OUT = os.path.join(ROOT, "docs", "img")
TABS = ["app_results", "app_chart", "app_trials", "app_generator", "app_help"]


def wait(application: QApplication, seconds: float) -> None:
    """Пауза с обработкой событий окна."""
    end = time.time() + seconds
    while time.time() < end:
        application.processEvents()
        time.sleep(0.02)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    application = QApplication(sys.argv)
    application.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    while window.result is None:
        wait(application, 0.1)
    wait(application, 1.0)

    for index, name in enumerate(TABS):
        window.tabs.setCurrentIndex(index)
        wait(application, 0.8)
        window.grab().save(os.path.join(OUT, f"{name}.png"))
        print("сохранено", f"{name}.png")

    window.tabs.setCurrentIndex(1)
    wait(application, 0.5)
    window.figure.savefig(os.path.join(OUT, "cost_curve.png"), dpi=150, facecolor="white")
    window.generator_figure.savefig(os.path.join(OUT, "prng_quality.png"), dpi=150, facecolor="white")
    print("сохранены графики cost_curve.png и prng_quality.png")
    window.close()


if __name__ == "__main__":
    main()
