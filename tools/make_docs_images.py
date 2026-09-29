"""Рисунки для README: схема регистра сдвига, блок-схема алгоритма, структура затрат.

Запуск: python tools/make_docs_images.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

from montecarlo.lfsr import POLYNOMIALS, polynomial_text
from montecarlo.model import Parameters, simulate

OUT = os.path.join(ROOT, "docs", "img")
ACCENT = "#1f6feb"
DARK = "#16233a"
GREEN = "#1a7f37"
ORANGE = "#b54708"


def lfsr_scheme(number: int = 9) -> None:
    """Схема сдвигового регистра: 32 ячейки и отводы обратной связи."""
    taps = set(POLYNOMIALS[number])
    figure, axes = plt.subplots(figsize=(15, 4.6))
    width, height, gap = 0.78, 0.7, 0.22
    for index in range(1, 33):
        x = (index - 1) * (width + gap)
        tapped = index in taps
        box = FancyBboxPatch(
            (x, 0), width, height,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.6,
            edgecolor=ACCENT if tapped else "#9fb3cd",
            facecolor="#e8f0fe" if tapped else "white",
        )
        axes.add_patch(box)
        axes.text(x + width / 2, height / 2, str(index), ha="center", va="center",
                  fontsize=8.5, color=DARK, fontweight="bold" if tapped else "normal")
        if index < 32:
            axes.add_patch(FancyArrowPatch(
                (x + width, height / 2), (x + width + gap, height / 2),
                arrowstyle="-|>", mutation_scale=9, color="#6b7c93", linewidth=1.1))
        if tapped:
            axes.add_patch(FancyArrowPatch(
                (x + width / 2, height), (x + width / 2, 1.55),
                arrowstyle="-|>", mutation_scale=9, color=ACCENT, linewidth=1.1))

    right = 31 * (width + gap) + width
    axes.plot([-0.9, right], [1.55, 1.55], color=ACCENT, linewidth=1.4)
    axes.plot([right, right], [height / 2, 1.55], color=ACCENT, linewidth=1.4)
    axes.add_patch(FancyArrowPatch((-0.9, 1.55), (-0.9, height / 2 + 0.02),
                                   arrowstyle="-|>", mutation_scale=11, color=ACCENT, linewidth=1.4))
    axes.add_patch(FancyArrowPatch((-0.9, height / 2), (0, height / 2),
                                   arrowstyle="-|>", mutation_scale=11, color=ACCENT, linewidth=1.4))
    axes.text(right / 2, 1.55, " ⊕ сумма по модулю 2 ", ha="center", va="center",
              fontsize=11, color=ACCENT, zorder=6,
              bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor=ACCENT, linewidth=1.4))

    axes.text(right / 2, 2.15, f"Обратная связь: разряды, отмеченные полиномом № {number}",
              ha="center", fontsize=11, color=DARK, fontweight="bold")
    axes.text(right / 2, -0.55, polynomial_text(number), ha="center", fontsize=9.5, color="#4a5a72")
    axes.text(right + 0.2, height / 2 - 0.45, "выход:\n32 бита → одно число",
              ha="center", fontsize=9, color=GREEN)
    axes.set_xlim(-1.6, right + 1.4)
    axes.set_ylim(-0.9, 2.5)
    axes.axis("off")
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "lfsr_scheme.png"), dpi=150, facecolor="white")
    plt.close(figure)


def _block(axes, x, y, w, h, text, color, shape="round"):
    """Прямоугольник блок-схемы с текстом."""
    style = "round,pad=0.02,rounding_size=0.12" if shape == "round" else "square,pad=0.02"
    axes.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, linewidth=1.6,
                                  edgecolor=color, facecolor="white"))
    axes.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9.5, color=DARK)


def _arrow(axes, start, end, text="", color="#6b7c93", offset=(0.0, 0.18)):
    """Стрелка блок-схемы; подпись ставится рядом с линией, а не поверх неё."""
    axes.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12,
                                   color=color, linewidth=1.3))
    if text:
        axes.text((start[0] + end[0]) / 2 + offset[0], (start[1] + end[1]) / 2 + offset[1], text,
                  fontsize=9, color=color, ha="center", va="bottom",
                  bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none"))


def algorithm_scheme() -> None:
    """Блок-схема: что происходит с одним резистором за одно испытание."""
    figure, axes = plt.subplots(figsize=(9.5, 8.2))
    _block(axes, 3.0, 9.2, 3.6, 0.7, "Разыграть R1 и R2", ACCENT)
    _block(axes, 3.0, 7.9, 3.6, 0.7, "R1 < P ?", ORANGE)
    _block(axes, 0.3, 6.4, 3.4, 0.8, "Резистор проверяют:\nзатраты + B", ACCENT)
    _block(axes, 5.9, 6.4, 3.4, 0.8, "Резистор не проверяют", "#9fb3cd")
    _block(axes, 0.3, 4.8, 3.4, 0.8, "R2 < A ?\n(если нет — затрат нет)", ORANGE)
    _block(axes, 5.9, 4.8, 3.4, 0.8, "R2 < A ?\n(если нет — затрат нет)", ORANGE)
    _block(axes, 0.3, 3.4, 3.4, 0.8, "Брак выявлен:\nзатраты + C", GREEN)
    _block(axes, 5.9, 3.4, 3.4, 0.8, "Брак попал в изделие:\nзатраты + D", "#b3261e")
    _block(axes, 3.0, 1.9, 3.6, 0.8, "Накопить общие затраты\nи перейти к следующему", ACCENT)
    _block(axes, 3.0, 0.5, 3.6, 0.8, "Повторить для всех долей P\nот 0 до 100 % и выбрать минимум", DARK)

    _arrow(axes, (4.8, 9.2), (4.8, 8.6))
    _arrow(axes, (3.0, 8.25), (2.0, 8.25), "да", ORANGE, offset=(0.0, 0.12))
    _arrow(axes, (2.0, 8.25), (2.0, 7.2), "", ORANGE)
    _arrow(axes, (6.6, 8.25), (7.6, 8.25), "нет", ORANGE, offset=(0.0, 0.12))
    _arrow(axes, (7.6, 8.25), (7.6, 7.2), "", ORANGE)
    _arrow(axes, (2.0, 6.4), (2.0, 5.6))
    _arrow(axes, (7.6, 6.4), (7.6, 5.6))
    _arrow(axes, (2.0, 4.8), (2.0, 4.2), "да", ORANGE, offset=(0.30, -0.12))
    _arrow(axes, (7.6, 4.8), (7.6, 4.2), "да", ORANGE, offset=(0.30, -0.12))
    _arrow(axes, (2.0, 3.4), (2.0, 2.3))
    _arrow(axes, (2.0, 2.3), (3.0, 2.3))
    _arrow(axes, (7.6, 3.4), (7.6, 2.3))
    _arrow(axes, (7.6, 2.3), (6.6, 2.3))
    _arrow(axes, (4.8, 1.9), (4.8, 1.3))

    axes.text(4.8, 10.3, "Одно испытание метода Монте-Карло", ha="center", fontsize=13,
              color=DARK, fontweight="bold")
    axes.text(4.8, 10.0, "P — доля контроля, A — доля негодных резисторов", ha="center",
              fontsize=9.5, color="#4a5a72")
    axes.set_xlim(0, 9.6)
    axes.set_ylim(0, 10.6)
    axes.axis("off")
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "algorithm.png"), dpi=150, facecolor="white")
    plt.close(figure)


def cost_structure() -> None:
    """Из чего складываются затраты при разной доле контроля."""
    result = simulate(Parameters())
    percents = [row.percent for row in result.rows]
    control = [row.control_cost for row in result.rows]
    fitting = [row.fitting_cost for row in result.rows]
    replace = [row.replace_cost for row in result.rows]

    figure, axes = plt.subplots(figsize=(9, 4.8))
    axes.bar(percents, control, width=3.4, label="контроль (B)", color="#1f6feb")
    axes.bar(percents, fitting, width=3.4, bottom=control, label="подгонка (C)", color="#f2a900")
    bottom = [c + f for c, f in zip(control, fitting)]
    axes.bar(percents, replace, width=3.4, bottom=bottom, label="замена в изделии (D)", color="#b3261e")
    axes.plot(percents, [row.total_cost for row in result.rows], color=DARK, linewidth=2, label="всего")
    axes.set_xlabel("Доля резисторов, проходящих входной контроль, %")
    axes.set_ylabel("Затраты, руб.")
    axes.set_title("Из чего складываются затраты (10 000 резисторов, вариант 3)")
    axes.legend()
    axes.grid(axis="y", alpha=0.3)
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "cost_structure.png"), dpi=150, facecolor="white")
    plt.close(figure)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    lfsr_scheme()
    algorithm_scheme()
    cost_structure()
    print("рисунки сохранены в", OUT)


if __name__ == "__main__":
    main()
