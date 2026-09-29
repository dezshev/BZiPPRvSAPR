"""Модель входного контроля резисторов и расчёт затрат методом Монте-Карло.

Постановка задачи (вариант 3). На предприятие поступают резисторы, из которых
примерно A % не подходят для изготовления продукции и требуют подгонки.
Контроль одного резистора стоит B рублей, подгонка выявленного резистора — C рублей.
Если негодный резистор не выявили и установили в изделие, его замена стоит D рублей.
Нужно найти долю резисторов, которую выгодно подвергать входному контролю.

Ход одного испытания повторяет алгоритм из методических указаний:
разыгрываются два псевдослучайных числа R1 и R2;
R1 определяет, попал ли резистор на контроль, R2 — годен ли он.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .lfsr import LFSR, VARIANT_3_POLYNOMIAL, polynomial_text


@dataclass
class Parameters:
    """Исходные данные задачи и настройки расчёта."""

    defect_percent: float = 10.0      # A — доля негодных резисторов, %
    cost_control: float = 4.0         # B — стоимость контроля одного резистора
    cost_fitting: float = 60.0        # C — стоимость подгонки выявленного резистора
    cost_replace: float = 140.0       # D — стоимость замены резистора в готовом изделии
    trials: int = 10_000              # количество испытаний (резисторов) на одну долю
    percent_step: int = 5             # шаг перебора доли контроля, %
    polynomial: int = VARIANT_3_POLYNOMIAL
    seed: int = 0x2025_5445

    @property
    def defect_share(self) -> float:
        """Доля негодных резисторов в долях единицы."""
        return self.defect_percent / 100.0

    def percents(self) -> list[int]:
        """Перебираемые доли контроля: от 0 до 100 % с заданным шагом."""
        values = list(range(0, 101, self.percent_step))
        if values[-1] != 100:
            values.append(100)
        return values

    def describe(self) -> str:
        """Короткое описание исходных данных для заголовков отчётов."""
        return (
            f"A = {self.defect_percent:g} %, B = {self.cost_control:g}, "
            f"C = {self.cost_fitting:g}, D = {self.cost_replace:g}, "
            f"испытаний {self.trials}, полином № {self.polynomial}"
        )

    def polynomial_text(self) -> str:
        return polynomial_text(self.polynomial)


@dataclass
class Trial:
    """Одно испытание — судьба одного резистора."""

    number: int
    r1: float
    r2: float
    controlled: bool
    defective: bool
    cost: float
    total: float

    @property
    def event(self) -> str:
        """Что произошло с резистором — понятная расшифровка для таблицы."""
        if self.controlled and self.defective:
            return "контроль и подгонка"
        if self.controlled:
            return "только контроль"
        if self.defective:
            return "замена в изделии"
        return "затрат нет"


@dataclass
class PercentResult:
    """Итог моделирования для одной доли контроля."""

    percent: int
    total_cost: float
    control_cost: float
    fitting_cost: float
    replace_cost: float
    controlled: int
    fitted: int
    replaced: int
    expected_cost: float          # теоретическое значение затрат

    @property
    def cost_per_resistor(self) -> float:
        return self.total_cost

    @property
    def deviation(self) -> float:
        """Отклонение результата моделирования от теоретического значения, %."""
        if self.expected_cost == 0:
            return 0.0
        return (self.total_cost - self.expected_cost) / self.expected_cost * 100.0


@dataclass
class SimulationResult:
    """Результат полного расчёта по всем долям контроля."""

    parameters: Parameters
    rows: list[PercentResult]
    trials_example: list[Trial] = field(default_factory=list)
    example_percent: int = 0
    numbers: list[tuple[float, float]] = field(default_factory=list)

    @property
    def best(self) -> PercentResult:
        """Доля контроля с наименьшими общими затратами."""
        return min(self.rows, key=lambda row: row.total_cost)

    @property
    def worst(self) -> PercentResult:
        return max(self.rows, key=lambda row: row.total_cost)

    @property
    def best_expected(self) -> PercentResult:
        """Лучшая доля контроля по теоретической формуле."""
        return min(self.rows, key=lambda row: row.expected_cost)

    def saving(self) -> float:
        """Экономия лучшего варианта по сравнению с худшим."""
        return self.worst.total_cost - self.best.total_cost


def expected_cost(params: Parameters, share: float) -> float:
    """Теоретические затраты при доле контроля share.

    Каждый резистор с вероятностью share попадает на контроль (затраты B),
    и тогда с вероятностью A требует подгонки (ещё C). Резистор без контроля
    с вероятностью A потребует замены в изделии (D).
    """
    a = params.defect_share
    per_resistor = share * params.cost_control + share * a * params.cost_fitting + (1 - share) * a * params.cost_replace
    return per_resistor * params.trials


def generate_numbers(params: Parameters) -> list[tuple[float, float]]:
    """Пары псевдослучайных чисел для всех испытаний.

    Один и тот же набор чисел используется для всех долей контроля.
    Это приём общих случайных чисел: доли сравниваются в одинаковых условиях,
    поэтому график затрат получается ровным, а не «дёрганым».
    """
    generator = LFSR.from_polynomial(params.polynomial, params.seed)
    return generator.random_pairs(params.trials)


def run_percent(params: Parameters, percent: int, numbers: list[tuple[float, float]]) -> PercentResult:
    """Моделирование всех испытаний для одной доли контроля."""
    share = percent / 100.0
    defect = params.defect_share
    controlled = fitted = replaced = 0

    for r1, r2 in numbers:
        if r1 < share:
            controlled += 1
            if r2 < defect:
                fitted += 1
        elif r2 < defect:
            replaced += 1

    control_cost = controlled * params.cost_control
    fitting_cost = fitted * params.cost_fitting
    replace_cost = replaced * params.cost_replace
    return PercentResult(
        percent=percent,
        total_cost=control_cost + fitting_cost + replace_cost,
        control_cost=control_cost,
        fitting_cost=fitting_cost,
        replace_cost=replace_cost,
        controlled=controlled,
        fitted=fitted,
        replaced=replaced,
        expected_cost=expected_cost(params, share),
    )


def collect_trials(params: Parameters, percent: int, numbers: list[tuple[float, float]], limit: int = 200) -> list[Trial]:
    """Подробная таблица первых испытаний — как таблица 1 в методических указаниях."""
    share = percent / 100.0
    defect = params.defect_share
    trials: list[Trial] = []
    total = 0.0
    for index, (r1, r2) in enumerate(numbers[:limit], start=1):
        controlled = r1 < share
        defective = r2 < defect
        cost = 0.0
        if controlled:
            cost += params.cost_control
            if defective:
                cost += params.cost_fitting
        elif defective:
            cost += params.cost_replace
        total += cost
        trials.append(Trial(index, r1, r2, controlled, defective, cost, total))
    return trials


def simulate(params: Parameters, example_percent: int | None = None, example_limit: int = 200) -> SimulationResult:
    """Полный расчёт: перебор долей контроля от 0 до 100 %."""
    numbers = generate_numbers(params)
    rows = [run_percent(params, percent, numbers) for percent in params.percents()]
    if example_percent is None:
        example_percent = params.percents()[1] if len(params.percents()) > 1 else 0
    trials = collect_trials(params, example_percent, numbers, example_limit)
    return SimulationResult(
        parameters=params,
        rows=rows,
        trials_example=trials,
        example_percent=example_percent,
        numbers=numbers,
    )
