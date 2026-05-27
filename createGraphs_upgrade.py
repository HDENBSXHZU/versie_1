"""
createGraphs_upgrade.py
=======================
Genereert een HTML-grafiek met 4 subplots op basis van het CSV
van receiver_upgrade.py:
  1. Gemiddelde latentie (ms)
  2. CPU-gebruik (%)
  3. Geheugengebruik (MB)
  4. Percentage ontvangen berichten (%)

Installatie: pip3 install plotly pandas

Gebruik:
  python3 createGraphs_upgrade.py
  python3 createGraphs_upgrade.py --input latency_results.csv
  python3 createGraphs_upgrade.py --input latency_results.csv --no-browser
"""

import argparse
import os
import sys

try:
    import pandas as pd
except ImportError:
    sys.exit("pip3 install pandas")

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    sys.exit("pip3 install plotly")


KLEUR = "#1f77b4"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input",      default="latency_results.csv")
    p.add_argument("--output",     default=".")
    p.add_argument("--no-browser", action="store_true")
    return p.parse_args()


def evolutie(waarden):
    result = ["—"]
    for i in range(1, len(waarden)):
        vorig = waarden[i - 1]
        if vorig == 0:
            result.append("—")
        else:
            pct   = (waarden[i] - vorig) / vorig * 100
            teken = "+" if pct >= 0 else ""
            result.append(f"{teken}{pct:.2f}%")
    return result


def main():
    args = parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"Bestand niet gevonden: {args.input}")

    df = pd.read_csv(args.input)

    for k in ["hz", "avg_latency_ms", "std_latency_ms", "pct_ontvangen",
              "cpu_percent", "mem_mb"]:
        if k in df.columns:
            df[k] = pd.to_numeric(df[k], errors="coerce")

    df = df.dropna(subset=["hz", "avg_latency_ms"]).sort_values("hz")

    heeft_cpu = "cpu_percent" in df.columns and df["cpu_percent"].notna().any()
    heeft_mem = "mem_mb"      in df.columns and df["mem_mb"].notna().any()

    print(f"Geladen: {len(df)} blokken")

    hz  = df["hz"].tolist()
    gem = df["avg_latency_ms"].tolist()
    std = df["std_latency_ms"].tolist() if "std_latency_ms" in df.columns else [0] * len(hz)
    pct = df["pct_ontvangen"].tolist()  if "pct_ontvangen"  in df.columns else [100] * len(hz)
    cpu = df["cpu_percent"].tolist()    if heeft_cpu else [None] * len(hz)
    mem = df["mem_mb"].tolist()         if heeft_mem else [None] * len(hz)
    ev  = evolutie(gem)

    boven = [g + s         for g, s in zip(gem, std)]
    onder = [max(0, g - s) for g, s in zip(gem, std)]

    r, g_c, b = int(KLEUR[1:3], 16), int(KLEUR[3:5], 16), int(KLEUR[5:7], 16)
    fill = f"rgba({r},{g_c},{b},0.15)"

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=(
            "Gemiddelde latentie (ms)",
            "CPU-gebruik (%)",
            "Geheugengebruik (MB)",
            "Ontvangen berichten (%)",
        )
    )

    # ── Subplot 1: latentie ───────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=hz + hz[::-1], y=boven + onder[::-1],
        fill="toself", fillcolor=fill,
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=hz, y=gem,
        mode="lines+markers",
        name="Gem. latentie",
        line=dict(color=KLEUR, width=2.5),
        marker=dict(size=8),
        customdata=ev,
        hovertemplate=(
            "Hz: %{x:.0f}<br>"
            "Gem. latentie: %{y:.3f} ms<br>"
            "Verandering t.o.v. vorig: %{customdata}"
            "<extra></extra>"
        ),
    ), row=1, col=1)

    # ── Subplot 2: CPU ────────────────────────────────────────────────────
    if heeft_cpu:
        fig.add_trace(go.Scatter(
            x=hz, y=cpu,
            mode="lines+markers",
            name="CPU%",
            line=dict(color=KLEUR, width=2.5, dash="dot"),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate=(
                "Hz: %{x:.0f}<br>"
                "CPU: %{y:.1f}%"
                "<extra></extra>"
            ),
        ), row=2, col=1)

    # ── Subplot 3: geheugen ───────────────────────────────────────────────
    if heeft_mem:
        fig.add_trace(go.Scatter(
            x=hz, y=mem,
            mode="lines+markers",
            name="RAM (MB)",
            line=dict(color=KLEUR, width=2.5, dash="dashdot"),
            marker=dict(size=8, symbol="triangle-up"),
            hovertemplate=(
                "Hz: %{x:.0f}<br>"
                "RAM: %{y:.0f} MB"
                "<extra></extra>"
            ),
        ), row=3, col=1)

    # ── Subplot 4: pakketverlies ──────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=hz, y=pct,
        mode="lines+markers",
        name="% Ontvangen",
        line=dict(color=KLEUR, width=2.5, dash="dash"),
        marker=dict(size=8, symbol="square"),
        hovertemplate=(
            "Hz: %{x:.0f}<br>"
            "Ontvangen: %{y:.2f}%"
            "<extra></extra>"
        ),
    ), row=4, col=1)

    # Referentielijn 100%
    fig.add_trace(go.Scatter(
        x=[min(hz), max(hz)], y=[100, 100],
        mode="lines",
        line=dict(color="gray", width=1, dash="dot"),
        showlegend=False,
    ), row=4, col=1)

    fig.update_layout(
        title=dict(
            text="ROS2 Latentiemeting — VM1 \u2192 VM3",
            font=dict(size=15),
        ),
        hovermode="x unified",
        template="plotly_white",
        height=1100,
        font=dict(family="Arial", size=13),
        legend=dict(x=1.01, y=1.0,
                    bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="#ccc", borderwidth=1),
    )

    fig.update_yaxes(title_text="Latentie (ms)", rangemode="tozero", gridcolor="#e0e0e0", row=1, col=1)
    fig.update_yaxes(title_text="CPU (%)",        rangemode="tozero", gridcolor="#e0e0e0", row=2, col=1)
    fig.update_yaxes(title_text="RAM (MB)",       rangemode="tozero", gridcolor="#e0e0e0", row=3, col=1)
    fig.update_yaxes(title_text="% Ontvangen",   range=[0, 105],     gridcolor="#e0e0e0", row=4, col=1)
    fig.update_xaxes(title_text="Frequentie (berichten/s)", gridcolor="#e0e0e0", row=4, col=1)

    os.makedirs(args.output, exist_ok=True)
    pad = os.path.join(args.output, "latentie.html")
    fig.write_html(pad)
    print(f"Grafiek opgeslagen: {pad}")

    if not args.no_browser:
        fig.show()


if __name__ == "__main__":
    main()
