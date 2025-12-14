#
# Thanks, ChatGPT 5.2
#

import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Callable

# ---------- helpers ----------

def _nice_step(raw_step: float) -> float:
    """
    Round raw_step to a "nice" step: 1, 2, 2.5, 5, 10 × 10^k
    """
    if raw_step <= 0 or not math.isfinite(raw_step):
        return 1.0
    exp = math.floor(math.log10(raw_step))
    f = raw_step / (10 ** exp)
    # You can tweak this candidate set if you prefer fewer/more tick densities.
    candidates = [1.0, 2.0, 2.5, 5.0, 10.0]
    best = min(candidates, key=lambda c: abs(c - f))
    return best * (10 ** exp)

def _floor_to_step(x: float, step: float) -> float:
    return math.floor(x / step) * step

def _ceil_to_step(x: float, step: float) -> float:
    return math.ceil(x / step) * step

def _frange(start: float, stop: float, step: float, *, eps: float = 1e-12) -> List[float]:
    # inclusive stop with tolerance
    n = int(math.floor((stop - start) / step + 1 + eps))
    return [start + i * step for i in range(max(n, 0) + 1) if start + i * step <= stop + eps]

def _trim_float(x: float, digits: int = 12) -> float:
    # Helps avoid 1.2000000000000002 artifacts
    return float(f"{x:.{digits}g}")

def _format_sig(x: float, sig: int = 6) -> str:
    if x == 0:
        return "0"
    ax = abs(x)
    # switch to scientific for big/small
    if ax >= 1e6 or ax < 1e-3:
        return f"{x:.{sig-1}e}"
    # otherwise use general with sig figs
    return f"{x:.{sig}g}"

# ---------- public API ----------

@dataclass(frozen=True)
class TickResult:
    tickvals: List[float]
    ticktext: Optional[List[str]] = None  # if you want custom labels

def nice_linear_ticks(vmin: float, vmax: float, nticks: int = 6) -> TickResult:
    """
    Produce "nice" linear ticks spanning [vmin, vmax].
    Returns tick values (and no custom labels by default).
    """
    if not (math.isfinite(vmin) and math.isfinite(vmax)):
        return TickResult([])
    if vmin == vmax:
        # expand a bit around the value
        vmin, vmax = vmin - 0.5, vmax + 0.5

    if vmin > vmax:
        vmin, vmax = vmax, vmin

    span = vmax - vmin
    raw_step = span / max(nticks - 1, 1)
    step = _nice_step(raw_step)

    start = _floor_to_step(vmin, step)
    stop  = _ceil_to_step(vmax, step)

    vals = [_trim_float(x) for x in _frange(start, stop, step)]
    return TickResult(vals)

def log_ticks_for_logged_data(
    log_vmin: float,
    log_vmax: float,
    base: float = 10.0,
    *,
    major_every: int = 1,
    minor: bool = True,
    minor_subticks: Tuple[int, ...] = (2,3,4,5,6,7,8,9),
    label_major_only: bool = True,
    sigfig: int = 6,
    exponent_formatter: Optional[Callable[[int], str]] = None
) -> TickResult:
    """
    You already plotted y = log_base(x). This returns tickvals in *log space*
    but tick labels in linear space (x).

    Example: if axis shows log10(x) values, tickvals are [1,2,3] and ticktext are ["10","100","1000"].
    """
    if not (math.isfinite(log_vmin) and math.isfinite(log_vmax)):
        return TickResult([])

    if log_vmin > log_vmax:
        log_vmin, log_vmax = log_vmax, log_vmin

    emin = math.floor(log_vmin)
    emax = math.ceil(log_vmax)

    tickvals: List[float] = []
    ticktext: List[str] = []

    if exponent_formatter is None:
        def exponent_formatter(e: int) -> str:
            # default: show 10^e as a plain number if reasonable
            val = base ** e
            return _format_sig(val, sig=sigfig)

    for e in range(emin, emax + 1):
        if (e - emin) % max(major_every, 1) == 0:
            # major tick at base^e => log position = e
            if e >= log_vmin - 1e-12 and e <= log_vmax + 1e-12:
                tickvals.append(float(e))
                ticktext.append(exponent_formatter(e))
        if minor:
            # minor ticks between e and e+1: log(base^e * k) = e + log(k)/log(base)
            if e == emax:
                continue
            for k in minor_subticks:
                pos = e + math.log(k, base)
                if pos >= log_vmin - 1e-12 and pos <= log_vmax + 1e-12:
                    tickvals.append(pos)
                    if label_major_only:
                        ticktext.append("")  # no label
                    else:
                        ticktext.append(_format_sig((base ** e) * k, sig=sigfig))

    # sort (because we interleave majors/minors)
    pairs = sorted(zip(tickvals, ticktext), key=lambda t: t[0])
    tickvals = [_trim_float(v) for v, _ in pairs]
    ticktext = [s for _, s in pairs]
    return TickResult(tickvals, ticktext)


def log10_ticks_for_logged_data_superscript(
    log_vmin: float,
    log_vmax: float,
    *,
    major_every: int = 1,
    minor: bool = True,
    minor_subticks: Tuple[int, ...] = (2,3,4,5,6,7,8,9),
    label_major_only: bool = True,
) -> TickResult:
    """
    Data already has log10 applied. Returns tickvals in log10 space.
    Major labels are always formatted as: 10<sup>n</sup>
    """
    if not (math.isfinite(log_vmin) and math.isfinite(log_vmax)):
        return TickResult([])
    if log_vmin > log_vmax:
        log_vmin, log_vmax = log_vmax, log_vmin

    emin = math.floor(log_vmin)
    emax = math.ceil(log_vmax)

    tickvals: List[float] = []
    ticktext: List[str] = []

    def major_label(e: int) -> str:
        return f"10<sup>{e}</sup>"

    for e in range(emin, emax + 1):
        # major at integer exponent
        if (e - emin) % max(major_every, 1) == 0:
            pos = float(e)
            if pos >= log_vmin - 1e-12 and pos <= log_vmax + 1e-12:
                tickvals.append(pos)
                ticktext.append(major_label(e))

        # minors between e and e+1
        if minor and e < emax:
            for k in minor_subticks:
                pos = e + math.log10(k)
                if pos >= log_vmin - 1e-12 and pos <= log_vmax + 1e-12:
                    tickvals.append(pos)
                    ticktext.append("" if label_major_only else f"{k}×{major_label(e)}")

    # sort by position
    pairs = sorted(zip(tickvals, ticktext), key=lambda t: t[0])
    tickvals = [v for v, _ in pairs]
    ticktext = [s for _, s in pairs]
    return TickResult(tickvals, ticktext)


# ---------- convenience for Plotly ----------

def plotly_tick_array(ticks: TickResult) -> dict:
    """
    Build a Plotly axis dict chunk for tickmode='array'.
    """
    d = {"tickmode": "array", "tickvals": ticks.tickvals}
    if ticks.ticktext is not None:
        d["ticktext"] = ticks.ticktext
    return d
