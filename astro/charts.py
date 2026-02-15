"""Terminal chart rendering using plotext."""

import sys

import plotext as plt

from astro import fmt


def render_chart(
    chart_type: str,
    x_data: list,
    y_data: list,
    x_label: str = "",
    y_label: str = "",
    title: str = "",
) -> None:
    """Render a chart to stderr using plotext."""
    plt.clear_figure()
    plt.clear_data()
    plt.plotsize(70, 18)
    plt.theme("pro")

    match chart_type:
        case "bar":
            plt.bar(x_data or list(range(len(y_data))), y_data)
        case "line":
            plt.plot(x_data or list(range(len(y_data))), y_data)
        case "scatter":
            plt.scatter(x_data or list(range(len(y_data))), y_data)
        case "histogram":
            plt.hist(y_data)
        case _:
            raise ValueError(f"Unsupported chart type: {chart_type}")

    if title:
        plt.title(title)
    if x_label:
        plt.xlabel(x_label)
    if y_label:
        plt.ylabel(y_label)

    print(file=sys.stderr)
    print(plt.build(), file=sys.stderr)
    print(file=sys.stderr)
