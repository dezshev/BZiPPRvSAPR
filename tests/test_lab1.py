"""Проверки генератора псевдослучайных чисел и модели входного контроля.

Запуск из папки проекта: python -m unittest discover -s tests -v
"""

import os
import statistics
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from montecarlo.lfsr import LFSR, POLYNOMIALS
from montecarlo.model import Parameters, collect_trials, expected_cost, generate_numbers, run_percent, simulate


class TestGenerator(unittest.TestCase):
    """Свойства псевдослучайных чисел."""

    def setUp(self) -> None:
        self.generator = LFSR.from_polynomial(9)

    def test_numbers_in_range(self):
        """Все числа лежат строго внутри диапазона (0; 1)."""
        numbers = [self.generator.random() for _ in range(20_000)]
        self.assertTrue(all(0.0 < value < 1.0 for value in numbers))

    def test_mean_and_variance(self):
        """Среднее близко к 0,5, дисперсия — к 1/12."""
        numbers = [self.generator.random() for _ in range(50_000)]
        self.assertAlmostEqual(statistics.mean(numbers), 0.5, delta=0.01)
        self.assertAlmostEqual(statistics.pvariance(numbers), 1 / 12, delta=0.005)

    def test_uniform_by_intervals(self):
        """Числа равномерно заполняют десять интервалов: критерий χ² не превышает границу."""
        numbers = [self.generator.random() for _ in range(50_000)]
        counts = [0] * 10
        for value in numbers:
            counts[min(9, int(value * 10))] += 1
        expected = len(numbers) / 10
        chi2 = sum((count - expected) ** 2 / expected for count in counts)
        self.assertLess(chi2, 16.92)  # уровень значимости 0,05, девять степеней свободы

    def test_fast_feedback_matches_direct(self):
        """Расчёт обратной связи через маску совпадает с прямым перебором отводов."""
        fast = LFSR.from_polynomial(9)
        quick_bits = [fast.step() for _ in range(200)]

        slow = LFSR.from_polynomial(9)
        state = slow.seed
        direct_bits = []
        for _ in range(200):
            feedback = 0
            for tap in slow.taps:
                feedback ^= (state >> (tap - 1)) & 1
            direct_bits.append((state >> 31) & 1)
            state = ((state << 1) | feedback) & 0xFFFFFFFF
        self.assertEqual(quick_bits, direct_bits)

    def test_no_short_cycle(self):
        """Регистр не возвращается в прежнее состояние на коротком отрезке."""
        seen = set()
        for _ in range(200_000):
            self.generator.step()
            self.assertNotIn(self.generator.state, seen)
            seen.add(self.generator.state)

    def test_zero_seed_rejected(self):
        """Нулевое начальное состояние недопустимо."""
        with self.assertRaises(ValueError):
            LFSR(POLYNOMIALS[9], seed=0)

    def test_all_polynomials_work(self):
        """Каждый полином из методических указаний даёт числа в нужном диапазоне."""
        for number in POLYNOMIALS:
            generator = LFSR.from_polynomial(number)
            values = [generator.random() for _ in range(500)]
            self.assertTrue(all(0.0 < value < 1.0 for value in values), f"полином № {number}")


class TestModel(unittest.TestCase):
    """Расчёт затрат."""

    def setUp(self) -> None:
        self.params = Parameters(trials=5_000)
        self.numbers = generate_numbers(self.params)

    def test_costs_match_manual_count(self):
        """Затраты совпадают с ручным подсчётом по тем же числам."""
        percent = 40
        share = percent / 100
        defect = self.params.defect_share
        manual = 0.0
        for r1, r2 in self.numbers:
            if r1 < share:
                manual += self.params.cost_control
                if r2 < defect:
                    manual += self.params.cost_fitting
            elif r2 < defect:
                manual += self.params.cost_replace
        self.assertAlmostEqual(run_percent(self.params, percent, self.numbers).total_cost, manual, places=6)

    def test_zero_percent_has_no_control(self):
        """При нулевой доле контроля никого не проверяют, платят только за замену."""
        row = run_percent(self.params, 0, self.numbers)
        self.assertEqual(row.controlled, 0)
        self.assertEqual(row.control_cost, 0)
        self.assertEqual(row.fitting_cost, 0)
        self.assertGreater(row.replace_cost, 0)

    def test_full_percent_checks_everyone(self):
        """При стопроцентном контроле проверяют все резисторы и замен нет."""
        row = run_percent(self.params, 100, self.numbers)
        self.assertEqual(row.controlled, self.params.trials)
        self.assertEqual(row.replaced, 0)

    def test_close_to_theory(self):
        """Моделирование отличается от теоретической формулы не больше чем на 3 %."""
        for percent in (0, 25, 50, 75, 100):
            row = run_percent(self.params, percent, self.numbers)
            self.assertLess(abs(row.deviation), 3.0, f"доля {percent} %")

    def test_expected_formula(self):
        """Теоретическая формула считается по условию задачи."""
        params = Parameters(defect_percent=10, cost_control=4, cost_fitting=60, cost_replace=140, trials=1000)
        self.assertAlmostEqual(expected_cost(params, 0.0), 1000 * 14.0)
        self.assertAlmostEqual(expected_cost(params, 1.0), 1000 * 10.0)

    def test_best_percent_for_variant_3(self):
        """Для варианта 3 выгодно проверять все резисторы."""
        result = simulate(Parameters(trials=10_000))
        self.assertEqual(result.best.percent, 100)
        self.assertEqual(result.best_expected.percent, 100)

    def test_trial_table_totals(self):
        """В таблице испытаний нарастающий итог совпадает с суммой затрат."""
        trials = collect_trials(self.params, 50, self.numbers, limit=100)
        self.assertEqual(len(trials), 100)
        self.assertAlmostEqual(trials[-1].total, sum(trial.cost for trial in trials), places=6)


if __name__ == "__main__":
    unittest.main()
