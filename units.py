"""Engineering unit conversion with dimensional checking.

Built for the conversions that keep turning up in OT tag databases: psi to
bar, degF to degC, mcf to m3, API gravity to density and the rest of the
legacy oil & gas set.

Units are stored as a linear transform into a base unit plus a dimension
vector. Temperature scales use the offset; API gravity uses a custom pair of
functions because it is not a linear scale.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Callable

MASS, LENGTH, TIME, TEMP = "mass", "length", "time", "temperature"


def dims(**kwargs: int) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((k, v) for k, v in kwargs.items() if v))


@dataclass(frozen=True)
class Unit:
    symbol: str
    factor: float
    dims: tuple[tuple[str, int], ...] = ()
    offset: float = 0.0
    note: str = ""
    to_base: Callable[[float], float] | None = None
    from_base: Callable[[float], float] | None = None

    def base(self, value: float) -> float:
        if self.to_base:
            return self.to_base(value)
        return value * self.factor + self.offset

    def value(self, base: float) -> float:
        if self.from_base:
            return self.from_base(base)
        return (base - self.offset) / self.factor


def _gravity_to_kgm3(api: float) -> float:
    return 999.016 * 141.5 / (api + 131.5)


def _kgm3_to_gravity(density: float) -> float:
    return 141.5 * 999.016 / density - 131.5


def _sg_to_kgm3(sg: float) -> float:
    return sg * 999.016


def _kgm3_to_sg(density: float) -> float:
    return density / 999.016


PRESSURE = dims(mass=1, length=-1, time=-2)
FLOW = dims(length=3, time=-1)
VOLUME = dims(length=3)
MASS_D = dims(mass=1)
LENGTH_D = dims(length=1)
POWER = dims(mass=1, length=2, time=-3)
ENERGY = dims(mass=1, length=2, time=-2)
DENSITY = dims(mass=1, length=-3)

UNITS: dict[str, Unit] = {}


def register(unit: Unit, *aliases: str) -> None:
    UNITS[unit.symbol] = unit
    for alias in aliases:
        UNITS[alias] = unit


# Pressure (base Pa)
register(Unit("Pa", 1.0, PRESSURE), "pascal")
register(Unit("kPa", 1e3, PRESSURE))
register(Unit("MPa", 1e6, PRESSURE))
register(Unit("bar", 1e5, PRESSURE))
register(Unit("mbar", 1e2, PRESSURE))
register(Unit("psi", 6894.757293168, PRESSURE), "psig")
register(Unit("kg/cm2", 98066.5, PRESSURE), "kgf/cm2")
register(Unit("inH2O", 249.08891, PRESSURE), "inWC")
register(Unit("ftH2O", 2989.0669, PRESSURE))
register(Unit("mmHg", 133.322387415, PRESSURE), "torr")

# Temperature (base K)
register(Unit("K", 1.0, dims(temperature=1)))
register(Unit("degC", 1.0, dims(temperature=1), offset=273.15), "C", "°C")
register(Unit("degF", 5 / 9, dims(temperature=1), offset=459.67 * 5 / 9), "F", "°F")
register(Unit("degR", 5 / 9, dims(temperature=1)), "R", "°R")

# Volume (base m3)
register(Unit("m3", 1.0, VOLUME), "m³")
register(Unit("L", 1e-3, VOLUME), "litre", "liter")
register(Unit("bbl", 0.158987294928, VOLUME), "barrel")
register(Unit("gal", 0.003785411784, VOLUME), "USgal")
register(Unit("impgal", 0.00454609, VOLUME), "UKgal")
register(Unit("mcf", 28.316846592, VOLUME, note="1000 scf at 60 degF, 14.696 psia"))
register(Unit("MMscf", 28316.846592, VOLUME), "MMcf")

# Flow (base m3/s)
register(Unit("m3/h", 1 / 3600, FLOW))
register(Unit("m3/d", 1 / 86400, FLOW))
register(Unit("L/min", 1 / 60000, FLOW), "lpm")
register(Unit("GPM", 6.30901964e-5, FLOW), "gpm", "USgpm")
register(Unit("bbl/d", 1.840130729e-6, FLOW), "bpd")
register(Unit("SCFM", 4.719474432e-4, FLOW, note="standard conditions, not mass flow"))
register(Unit("Nm3/h", 1 / 3600, FLOW), "Nm³/h")

# Mass (base kg)
register(Unit("kg", 1.0, MASS_D))
register(Unit("g", 1e-3, MASS_D))
register(Unit("lb", 0.45359237, MASS_D), "lbm")
register(Unit("tonne", 1000.0, MASS_D), "t")
register(Unit("ton", 907.18474, MASS_D), "short ton")

# Length (base m)
register(Unit("m", 1.0, LENGTH_D))
register(Unit("mm", 1e-3, LENGTH_D))
register(Unit("in", 0.0254, LENGTH_D), "inch")
register(Unit("ft", 0.3048, LENGTH_D))

# Power / energy (base W, J)
register(Unit("W", 1.0, POWER))
register(Unit("kW", 1e3, POWER))
register(Unit("MW", 1e6, POWER))
register(Unit("hp", 745.699871582, POWER))
register(Unit("J", 1.0, ENERGY))
register(Unit("kWh", 3.6e6, ENERGY))
register(Unit("MMBtu", 1.05505585262e9, ENERGY))
register(Unit("therm", 1.05506e8, ENERGY))

# Density / gravity (base kg/m3) - API and SG use non-linear transforms.
register(
    Unit(
        "API",
        1.0,
        DENSITY,
        note="API gravity, 141.5/(API+131.5) = SG at 60 degF",
        to_base=_gravity_to_kgm3,
        from_base=_kgm3_to_gravity,
    )
)
register(
    Unit(
        "SG",
        1.0,
        DENSITY,
        note="specific gravity relative to water at 60 degF",
        to_base=_sg_to_kgm3,
        from_base=_kgm3_to_sg,
    )
)
register(Unit("kg/m3", 1.0, DENSITY), "kg/m³")

DIMENSION_NAMES = {
    PRESSURE: "pressure",
    dims(temperature=1): "temperature",
    VOLUME: "volume",
    FLOW: "flow",
    MASS_D: "mass",
    LENGTH_D: "length",
    POWER: "power",
    ENERGY: "energy",
    DENSITY: "density",
}


def convert(value: float, source: str, target: str) -> float:
    try:
        src, dst = UNITS[source], UNITS[target]
    except KeyError as exc:
        raise KeyError(f"unknown unit {exc.args[0]!r}") from None
    if not src.dims or src.dims != dst.dims:
        raise ValueError(
            f"cannot convert {source} to {target}: "
            f"{DIMENSION_NAMES.get(src.dims, src.dims)} vs "
            f"{DIMENSION_NAMES.get(dst.dims, dst.dims)}"
        )
    return dst.value(src.base(float(value)))


def resolve(symbol: str) -> str:
    unit = UNITS[symbol]
    return unit.symbol


def format_value(value: float) -> str:
    if value == 0 or 1e-4 <= abs(value) < 1e9:
        return f"{value:.6g}"
    return f"{value:.4e}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="units",
        description="Dimensional engineering unit conversion, including legacy units.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("convert", help="convert VALUE FROM TO")
    p.add_argument("value", type=float)
    p.add_argument("source")
    p.add_argument("target")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("list", help="list units, optionally for one dimension")
    p.add_argument("dimension", nargs="?")

    args = parser.parse_args(argv)

    if args.command == "convert":
        try:
            result = convert(args.value, args.source, args.target)
        except (KeyError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(
                json.dumps(
                    {
                        "value": args.value,
                        "from": resolve(args.source),
                        "to": resolve(args.target),
                        "result": result,
                    }
                )
            )
        else:
            print(f"{format_value(args.value)} {args.source} = {format_value(result)} {args.target}")
        return 0

    seen = set()
    rows = []
    for unit in UNITS.values():
        name = DIMENSION_NAMES.get(unit.dims, "dimensionless")
        if args.dimension and name != args.dimension:
            continue
        key = (unit.symbol, unit.dims)
        if key in seen:
            continue
        seen.add(key)
        rows.append((name, unit.symbol, unit.note))
    for name, symbol, note in sorted(rows):
        print(f"{name:<12}{symbol:<10}{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
