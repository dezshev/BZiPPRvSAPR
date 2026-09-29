"""Генератор псевдослучайных чисел на сдвиговом регистре с линейной обратной связью (LFSR).

Регистр состоит из 32 ячеек. На каждом такте содержимое сдвигается на одну позицию,
а в освободившуюся ячейку записывается сумма по модулю 2 (операция XOR) тех разрядов,
номера которых заданы порождающим полиномом. Одно псевдослучайное число получается
из 32 последовательных выходных битов, поэтому соседние числа не связаны между собой.
"""

from __future__ import annotations

# Порождающие полиномы из методических указаний (номер варианта полинома -> степени X).
# Свободный член «+1» в списке не указывается: он задаёт вход регистра, а не отвод.
POLYNOMIALS: dict[int, tuple[int, ...]] = {
    1: (32, 30, 28, 27, 25, 22, 21, 20, 19, 18, 12, 10, 9, 6),
    2: (32, 30, 29, 26, 25, 24, 23, 20, 18, 9, 5, 1),
    3: (32, 28, 27, 26, 23, 22, 21, 20, 19, 18, 17, 12, 9, 5, 4, 2),
    4: (32, 30, 28, 25, 24, 23, 21, 20, 19, 18, 17, 13, 11, 9, 5, 4, 3, 1),
    5: (32, 31, 30, 29, 27, 26, 25, 24, 23, 21, 20, 17, 16, 14, 12, 9, 8, 7),
    6: (32, 31, 30, 29, 27, 25, 23, 21, 20, 19, 13, 10, 7, 6, 5, 4, 3, 1),
    7: (32, 30, 28, 27, 25, 24, 23, 21, 20, 19, 18, 16, 15, 14, 8, 6, 5, 3),
    8: (32, 29, 27, 26, 25, 23, 21, 17, 16, 15, 13, 12, 8, 5, 4, 3),
    9: (32, 31, 27, 26, 23, 22, 19, 18, 17, 16, 15, 12, 9, 8, 6, 5, 4, 3, 2, 1),
    10: (32, 31, 30, 29, 27, 24, 23, 22, 18, 9, 7, 6, 3, 2),
    11: (32, 31, 30, 28, 27, 24, 23, 21, 18, 16, 15, 13, 12, 11, 10, 9, 7, 6, 5, 2),
    12: (32, 29, 28, 23, 22, 21, 16, 13, 10, 6, 5, 4),
    13: (32, 31, 26, 25, 24, 22, 21, 20, 19, 16, 13, 12, 8, 2),
    14: (32, 28, 22, 21, 20, 19, 18, 16, 10, 8, 7, 3),
    15: (32, 30, 27, 26, 25, 23, 22, 21, 20, 19, 18, 17, 13, 6, 5, 4),
}

# Полином варианта 3 по таблице вариантов задания.
VARIANT_3_POLYNOMIAL = 9

BITS = 32
MODULO = 1 << BITS


def polynomial_text(number: int) -> str:
    """Запись полинома в привычном виде, например «X^32 + X^31 + ... + 1»."""
    taps = POLYNOMIALS[number]
    parts = [f"X^{t}" if t > 1 else "X" for t in taps]
    return " + ".join(parts) + " + 1"


class LFSR:
    """Сдвиговый регистр с линейной обратной связью.

    taps   — номера ячеек, которые участвуют в обратной связи;
    seed   — начальное состояние регистра, нулевым быть не может;
    bits   — разрядность регистра (по умолчанию 32).
    """

    def __init__(self, taps: tuple[int, ...], seed: int = 0x2025_5445, bits: int = BITS) -> None:
        if not taps:
            raise ValueError("Список отводов пуст: обратная связь не задана")
        if max(taps) > bits or min(taps) < 1:
            raise ValueError("Номера отводов выходят за пределы регистра")
        seed &= (1 << bits) - 1
        if seed == 0:
            raise ValueError("Нулевое начальное состояние недопустимо: регистр останется в нуле")
        self.bits = bits
        self.taps = tuple(sorted(taps, reverse=True))
        self.seed = seed
        self.state = seed
        self.steps = 0
        # Маска отводов: единицы стоят в тех разрядах, которые участвуют в обратной связи.
        # Бит обратной связи — это чётность количества единиц в отмеченных разрядах.
        self.mask = sum(1 << (tap - 1) for tap in self.taps)
        self.high_bit = 1 << (bits - 1)
        self.limit = (1 << bits) - 1

    @classmethod
    def from_polynomial(cls, number: int, seed: int = 0x2025_5445) -> "LFSR":
        """Создание генератора по номеру полинома из методических указаний."""
        return cls(POLYNOMIALS[number], seed)

    def reset(self) -> None:
        """Возврат регистра в начальное состояние."""
        self.state = self.seed
        self.steps = 0

    def cells(self) -> list[int]:
        """Содержимое ячеек регистра: первый элемент списка — ячейка №1."""
        return [(self.state >> i) & 1 for i in range(self.bits)]

    def step(self) -> int:
        """Один такт работы регистра. Возвращает бит, вышедший из последней ячейки."""
        state = self.state
        feedback = (state & self.mask).bit_count() & 1
        out = 1 if state & self.high_bit else 0
        self.state = ((state << 1) | feedback) & self.limit
        self.steps += 1
        return out

    def next_word(self) -> int:
        """Очередное целое число: 32 выходных бита регистра."""
        state = self.state
        mask, high, limit = self.mask, self.high_bit, self.limit
        word = 0
        for _ in range(self.bits):
            word = (word << 1) | (1 if state & high else 0)
            state = ((state << 1) | ((state & mask).bit_count() & 1)) & limit
        self.state = state
        self.steps += self.bits
        return word

    def random(self) -> float:
        """Очередное псевдослучайное число из диапазона (0; 1)."""
        return (self.next_word() + 0.5) / MODULO

    def random_pairs(self, count: int) -> list[tuple[float, float]]:
        """Список пар чисел (R1, R2): R1 отвечает за отбор на контроль, R2 — за годность."""
        return [(self.random(), self.random()) for _ in range(count)]
