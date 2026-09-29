"""Пример отчёта Excel и снимки его листов для README.

Скрипт создаёт книгу с проверкой расчёта, открывает её в Excel и снимает два листа.
Нужен установленный Excel и пакет pywin32. Запуск: python tools/make_excel_screenshot.py
"""

import ctypes
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import win32con  # noqa: E402
import win32gui  # noqa: E402
import win32ui  # noqa: E402
from PIL import Image  # noqa: E402
import win32com.client as win32  # noqa: E402

from montecarlo.excel_report import save_workbook  # noqa: E402
from montecarlo.model import Parameters, simulate  # noqa: E402

IMG = os.path.join(ROOT, "docs", "img")
EXAMPLE = os.path.join(ROOT, "docs", "example")
REPORT = os.path.join(EXAMPLE, "Проверка_ЛР1_Монте-Карло.xlsx")


def screenshot(window, path: str) -> None:
    """Снимок окна Excel."""
    left, top, right, bottom = win32gui.GetWindowRect(window)
    width, height = right - left, bottom - top
    source = win32gui.GetWindowDC(window)
    device = win32ui.CreateDCFromHandle(source)
    memory = device.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(device, width, height)
    memory.SelectObject(bitmap)
    ctypes.windll.user32.PrintWindow(window, memory.GetSafeHdc(), 2)
    info = bitmap.GetInfo()
    image = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]),
                             bitmap.GetBitmapBits(True), "raw", "BGRX", 0, 1)
    image.save(path)
    win32gui.DeleteObject(bitmap.GetHandle())
    memory.DeleteDC()
    device.DeleteDC()
    win32gui.ReleaseDC(window, source)


def main() -> None:
    os.makedirs(IMG, exist_ok=True)
    os.makedirs(EXAMPLE, exist_ok=True)
    result = simulate(Parameters())
    save_workbook(result, REPORT)
    print("отчёт сохранён:", REPORT)

    excel = win32.gencache.EnsureDispatch("Excel.Application")
    excel.Visible = True
    excel.DisplayAlerts = False
    excel.WindowState = win32con.SW_MAXIMIZE and -4137  # xlMaximized
    try:
        book = excel.Workbooks.Open(REPORT)
        excel.CalculateFullRebuild()
        window = win32gui.FindWindow("XLMAIN", None)
        time.sleep(1.5)

        book.Worksheets("Свод").Activate()
        excel.ActiveWindow.ScrollRow = 1
        time.sleep(1.2)
        screenshot(window, os.path.join(IMG, "excel_summary.png"))
        print("снимок листа «Свод» готов")

        book.Worksheets("Испытания").Activate()
        excel.ActiveWindow.ScrollRow = 1
        time.sleep(1.2)
        screenshot(window, os.path.join(IMG, "excel_trials.png"))
        print("снимок листа «Испытания» готов")

        book.Close(False)
    finally:
        excel.Quit()


if __name__ == "__main__":
    main()
