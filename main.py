//@version=5
strategy("LENV24 B1", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.08)

// === INPUTS ===
ma_window = input.int(4, "MA Window", minval=1)
buy1_offset = input.float(0.07, "Buy1 Envelope Offset (%)", step=0.01)

// === CALCULS ===
ma = ta.sma(close, ma_window)
buy1_line = ma * (1 - buy1_offset)
close_line = ma

// === ALERTES & ENTRÉES ===
long_condition = ta.crossover(close, buy1_line)
if long_condition
    strategy.entry("Buy1", strategy.long)

// === SORTIE ===
close_condition = ta.crossunder(close, close_line)
if close_condition
    strategy.close("Buy1")

// === VISUELS ===
plot(ma, title="MA", color=color.orange, linewidth=2)
plot(buy1_line, title="Buy1 Line", color=color.green, linewidth=1)
plot(close_line, title="Close Line", color=color.red, linewidth=1)

plotshape(long_condition, title="Achat B1", location=location.belowbar, color=color.green, style=shape.triangleup, size=size.small)
plotshape(close_condition, title="Vente", location=location.abovebar, color=color.red, style=shape.triangledown, size=size.small)

alertcondition(long_condition, title="Signal Buy1", message="{{ticker}} Buy1 Signal")
alertcondition(close_condition, title="Signal Close", message="{{ticker}} Close Signal")
