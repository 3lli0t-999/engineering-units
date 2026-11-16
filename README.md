# engineering-units

Dimensional unit conversion with a bias toward the units that turn up in OT
tag databases and legacy P&IDs.

```bash
$ python3 units.py convert 10 psi bar
10 psi = 0.689476 bar

$ python3 units.py convert 212 degF degC
212 degF = 100 degC

$ python3 units.py convert 35 API kg/m3
35 API = 849.014 kg/m3

$ python3 units.py convert 1 MMscf m3
1 MMscf = 28316.8 m3

$ python3 units.py list pressure
pressure    MPa
pressure    Pa
pressure    bar
...
```

## Why another unit library

Most conversion helpers treat temperature as a scale factor and quietly return
the wrong answer for degF/degC, and almost none know what an API degree, an
mcf, a therm or an imperial gallon is. This one stores a linear transform into
a base unit plus a dimension vector, so incompatible conversions fail loudly:

```
$ python3 units.py convert 5 kg bar
error: cannot convert kg to bar: mass vs pressure
```

API gravity and specific gravity use custom functions because they are not
linear scales.

## Included dimensions

| Dimension | Units |
|---|---|
| pressure | Pa, kPa, MPa, bar, mbar, psi/psig, kg/cm2, inH2O, ftH2O, mmHg |
| temperature | K, degC, degF, degR (offset aware) |
| volume | m3, L, bbl, gal, impgal, mcf, MMscf |
| flow | m3/h, m3/d, L/min, GPM, bbl/d, SCFM, Nm3/h |
| mass | kg, g, lb, tonne, ton |
| length | m, mm, in, ft |
| power / energy | W, kW, MW, hp / J, kWh, MMBtu, therm |
| density | kg/m3, SG, API gravity |

## Caveats

- `mcf`, `MMscf` and `SCFM` assume 60 degF and 14.696 psia. If your contract
  uses 15 degC / 101.325 kPa, adjust the factors - do not use these blindly for
  custody transfer.
- Fluid-specific gravity is referenced to water at 60 degF.
- No currency, no time zones, no uncertainty propagation.

The data model and conversion function are importable:

```python
from units import convert
convert(120, "degF", "degC")   # 48.888...
```

## License

MIT.

---

Maintained by Glen Marsh · Helix Corp Ltd
