"""Лабораторная работа № 1: принятие решений на основе метода Монте-Карло."""

from .lfsr import LFSR, POLYNOMIALS, polynomial_text
from .model import Parameters, SimulationResult, expected_cost, simulate

__all__ = [
    "LFSR",
    "POLYNOMIALS",
    "polynomial_text",
    "Parameters",
    "SimulationResult",
    "expected_cost",
    "simulate",
]
