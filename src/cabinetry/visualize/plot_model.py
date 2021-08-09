"""Visualizes fit models with matplotlib."""

import logging
import pathlib
from typing import Any, Dict, List, Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from . import utils


log = logging.getLogger(__name__)


def data_MC(
    histogram_dict_list: List[Dict[str, Any]],
    total_model_unc: np.ndarray,
    bin_edges: np.ndarray,
    figure_path: pathlib.Path,
    log_scale: Optional[bool] = None,
    log_scale_x: bool = False,
    label: str = "",
    close_figure: bool = False,
) -> None:
    """Draws a data/MC histogram with uncertainty bands and ratio panel.

    Args:
        histogram_dict_list (List[Dict[str, Any]]): list of samples (with info stored in
            one dict per sample)
        total_model_unc (np.ndarray): total model uncertainty, if specified this is used
            instead of calculating it via sum in quadrature, defaults to None
        bin_edges (np.ndarray): bin edges of histogram
        figure_path (pathlib.Path): path where figure should be saved
        log_scale (Optional[bool], optional): whether to use a logarithmic vertical
            axis, defaults to None (automatically determine whether to use linear or log
            scale)
        log_scale_x (bool, optional): whether to use logarithmic horizontal axis,
            defaults to False
        label (str, optional): label written on the figure, defaults to ""
        close_figure (bool, optional): whether to close each figure immediately after
            saving it, defaults to False (enable when producing many figures to avoid
            memory issues, prevents rendering in notebooks)
    """
    mc_histograms_yields = []
    mc_labels = []
    for h in histogram_dict_list:
        if h["isData"]:
            data_histogram_yields = h["yields"]
            data_histogram_stdev = np.sqrt(data_histogram_yields)
            data_label = h["label"]
        else:
            mc_histograms_yields.append(h["yields"])
            mc_labels.append(h["label"])

    mpl.style.use("seaborn-colorblind")

    fig = plt.figure(figsize=(6, 6))
    gs = fig.add_gridspec(nrows=2, ncols=1, hspace=0, height_ratios=[3, 1])
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    # increase font sizes
    for item in (
        [ax1.yaxis.label, ax2.xaxis.label, ax2.yaxis.label]
        + ax1.get_yticklabels()
        + ax2.get_xticklabels()
        + ax2.get_yticklabels()
    ):
        item.set_fontsize("large")

    # minor ticks on all axes
    for axis in [ax1.xaxis, ax1.yaxis, ax2.xaxis, ax2.yaxis]:
        axis.set_minor_locator(mpl.ticker.AutoMinorLocator())

    # plot MC stacked together
    total_yield = np.zeros_like(mc_histograms_yields[0])
    bin_right_edges = bin_edges[1:]
    bin_left_edges = bin_edges[:-1]
    bin_width = bin_right_edges - bin_left_edges
    bin_centers = 0.5 * (bin_left_edges + bin_right_edges)
    # center data visually in bins if horizontal log scale is used
    bin_centers_data = (
        np.power(10, 0.5 * (np.log10(bin_left_edges * bin_right_edges)))
        if log_scale_x
        else bin_centers
    )
    mc_containers = []
    for mc_sample_yield in mc_histograms_yields:
        mc_container = ax1.bar(
            bin_centers,
            mc_sample_yield,
            width=bin_width,
            bottom=total_yield,
        )
        mc_containers.append(mc_container)

        # add a black line on top of each sample
        line_x = [y for y in bin_edges for _ in range(2)][1:-1]
        line_y = [y for y in (mc_sample_yield + total_yield) for _ in range(2)]
        ax1.plot(line_x, line_y, "-", color="black", linewidth=0.5)

        total_yield += mc_sample_yield

    # add total MC uncertainty
    mc_unc_container = ax1.bar(
        bin_centers,
        2 * total_model_unc,
        width=bin_width,
        bottom=total_yield - total_model_unc,
        fill=False,
        linewidth=0,
        edgecolor="gray",
        hatch=3 * "/",
    )

    # plot data
    data_container = ax1.errorbar(
        bin_centers_data,
        data_histogram_yields,
        yerr=data_histogram_stdev,
        fmt="o",
        color="k",
    )

    # ratio plot
    ax2.plot(
        [bin_left_edges[0], bin_right_edges[-1]],
        [1, 1],
        "--",
        color="black",
        linewidth=1,
    )  # reference line along y=1

    # add uncertainty band around y=1
    rel_mc_unc = total_model_unc / total_yield
    ax2.bar(
        bin_centers,
        2 * rel_mc_unc,
        width=bin_width,
        bottom=1 - rel_mc_unc,
        fill=False,
        linewidth=0,
        edgecolor="gray",
        hatch=3 * "/",
    )

    # data in ratio plot
    data_model_ratio = data_histogram_yields / total_yield
    data_model_ratio_unc = data_histogram_stdev / total_yield
    ax2.errorbar(
        bin_centers_data,
        data_model_ratio,
        yerr=data_model_ratio_unc,
        fmt="o",
        color="k",
    )

    # get the highest single bin yield, from the sum of MC or data
    y_max = max(np.amax(total_yield), np.amax(data_histogram_yields))
    # lowest MC yield in single bin (not considering empty bins)
    y_min = np.amin(total_yield[np.nonzero(total_yield)])

    # use log scale if it is requested, otherwise determine scale setting:
    # if yields vary over more than 2 orders of magnitude, set y-axis to log scale
    if log_scale or (log_scale is None and (y_max / y_min) > 100):
        # log vertical axis scale and limits
        ax1.set_yscale("log")
        ax1.set_ylim([y_min / 10, y_max * 10])
        # add "_log" to the figure name
        figure_path = figure_path.with_name(
            figure_path.stem + "_log" + figure_path.suffix
        )
    else:
        # do not use log scale
        ax1.set_ylim([0, y_max * 1.5])  # 50% headroom

    # log scale for horizontal axes
    if log_scale_x:
        ax1.set_xscale("log")
        ax2.set_xscale("log")

    # figure label (region name)
    at = mpl.offsetbox.AnchoredText(
        label,
        loc="upper left",
        frameon=False,
        prop={"fontsize": "large", "linespacing": 1.5},
    )
    ax1.add_artist(at)

    # MC contributions in inverse order, such that first legend entry corresponds to
    # the last (highest) contribution to the stack
    all_containers = mc_containers[::-1] + [mc_unc_container, data_container]
    all_labels = mc_labels[::-1] + ["Uncertainty", data_label]
    ax1.legend(
        all_containers, all_labels, frameon=False, fontsize="large", loc="upper right"
    )

    ax1.set_xlim(bin_edges[0], bin_edges[-1])
    ax1.set_ylabel("events")
    ax1.set_xticklabels([])
    ax1.set_xticklabels([], minor=True)
    ax1.tick_params(axis="both", which="major", pad=8)  # tick label - axis padding
    ax1.tick_params(direction="in", top=True, right=True, which="both")

    ax2.set_xlim(bin_edges[0], bin_edges[-1])
    ax2.set_ylim([0.5, 1.5])
    ax2.set_xlabel(histogram_dict_list[0]["variable"])
    ax2.set_ylabel("data / model")
    ax2.set_yticks([0.5, 0.75, 1.0, 1.25, 1.5])
    ax2.set_yticklabels([0.5, 0.75, 1.0, 1.25, ""])
    ax2.tick_params(axis="both", which="major", pad=8)
    ax2.tick_params(direction="in", top=True, right=True, which="both")

    fig.tight_layout()

    utils._save_figure(fig, figure_path, close_figure)


def templates(
    nominal_histo: Dict[str, np.ndarray],
    up_histo_orig: Dict[str, np.ndarray],
    down_histo_orig: Dict[str, np.ndarray],
    up_histo_mod: Dict[str, np.ndarray],
    down_histo_mod: Dict[str, np.ndarray],
    bin_edges: np.ndarray,
    variable: str,
    figure_path: pathlib.Path,
    label: str = "",
    close_figure: bool = False,
) -> None:
    """Draws a nominal template and the associated up/down variations.

    If a variation template is an empty dict, it is not drawn.

    Args:
        nominal_histo (Dict[str, np.ndarray]): the nominal template
        up_histo_orig (Dict[str, np.ndarray]): original "up" variation
        down_histo_orig (Dict[str, np.ndarray]): original "down" variation
        up_histo_mod (Dict[str, np.ndarray]): "up" variation after post-processing
        down_histo_mod (Dict[str, np.ndarray]): "down" variation after post-processing
        bin_edges (np.ndarray): bin edges of histogram
        variable (str): variable name for the horizontal axis
        figure_path (pathlib.Path): path where figure should be saved
        label (str, optional): label written on the figure, defaults to ""
        close_figure (bool, optional): whether to close each figure immediately after
            saving it, defaults to False (enable when producing many figures to avoid
            memory issues, prevents rendering in notebooks)
    """
    bin_width = bin_edges[1:] - bin_edges[:-1]
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    mpl.style.use("seaborn-colorblind")
    fig = plt.figure(figsize=(8, 6))
    gs = fig.add_gridspec(nrows=2, ncols=1, hspace=0, height_ratios=[3, 1])
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    # ratio plot line through unity and stat. uncertainty of nominal
    ax2.plot(
        [bin_edges[0], bin_edges[-1]],
        [1, 1],
        "--",
        color="black",
        linewidth=1,
    )
    rel_nominal_stat_unc = nominal_histo["stdev"] / nominal_histo["yields"]
    ax2.bar(
        bin_centers,
        2 * rel_nominal_stat_unc,
        width=bin_width,
        bottom=1 - rel_nominal_stat_unc,
        fill=False,
        linewidth=0,
        edgecolor="gray",
        hatch=3 * "/",
    )

    colors = ["black", "C0", "C1", "C0", "C1"]
    linestyles = ["-", ":", ":", "--", "--"]
    all_templates = [
        nominal_histo,
        up_histo_orig,
        down_histo_orig,
        up_histo_mod,
        down_histo_mod,
    ]
    template_labels = [
        "nominal",
        "up (original)",
        "down (original)",
        "up (modified)",
        "down (modified)",
    ]

    # x positions for lines drawn showing the template distributions
    line_x = [y for y in bin_edges for _ in range(2)][1:-1]

    # draw templates
    for template, color, linestyle, template_label in zip(
        all_templates, colors, linestyles, template_labels
    ):
        if not template:
            # variation not defined
            continue

        # lines to show each template distribution
        line_y = [y for y in template["yields"] for _ in range(2)]

        ax1.plot(
            line_x,
            line_y,
            color=color,
            linestyle=linestyle,
            label=template_label,
        )
        if template_label == "nominal":
            # band for stat. uncertainty of nominal prediction
            ax1.bar(
                bin_centers,
                2 * nominal_histo["stdev"],
                width=bin_width,
                bottom=nominal_histo["yields"] - nominal_histo["stdev"],
                fill=False,
                linewidth=0,
                edgecolor="gray",
                hatch=3 * "/",
            )
        else:
            # error bars for up/down variations
            ax1.errorbar(
                bin_centers,
                template["yields"],
                yerr=template["stdev"],
                fmt="none",
                color=color,
            )

            # ratio plot: variation / nominal
            template_ratio_plot = template["yields"] / nominal_histo["yields"]
            line_y = [y for y in template_ratio_plot for _ in range(2)]

            ax2.plot(
                line_x,
                line_y,
                color=color,
                linestyle=linestyle,
            )
            ax2.errorbar(
                bin_centers,
                template_ratio_plot,
                yerr=template["stdev"] / nominal_histo["yields"],
                fmt="none",
                color=color,
            )

    # increase font sizes
    for item in (
        [ax1.yaxis.label, ax2.xaxis.label, ax2.yaxis.label]
        + ax1.get_yticklabels()
        + ax2.get_xticklabels()
        + ax2.get_yticklabels()
    ):
        item.set_fontsize("large")

    # minor ticks on all axes
    for axis in [ax1.xaxis, ax1.yaxis, ax2.xaxis, ax2.yaxis]:
        axis.set_minor_locator(mpl.ticker.AutoMinorLocator())

    # figure label (region, sample, systematic name)
    at = mpl.offsetbox.AnchoredText(
        label,
        loc="upper left",
        frameon=False,
        prop={"fontsize": "large", "linespacing": 1.5},
    )
    ax1.add_artist(at)

    ax1.legend(frameon=False, fontsize="large", loc="upper right")

    max_yield = max(max(template["yields"]) for template in all_templates if template)

    ax1.set_xlim([bin_edges[0], bin_edges[-1]])
    ax1.set_ylim([0, max_yield * 1.75])
    ax1.set_ylabel("events")
    ax1.set_xticklabels([])
    ax1.tick_params(axis="both", which="major", pad=8)  # tick label - axis padding
    ax1.tick_params(direction="in", top=True, right=True, which="both")

    ax2.set_xlim([bin_edges[0], bin_edges[-1]])
    ax2.set_ylim([0.5, 1.5])
    ax2.set_xlabel(variable)
    ax2.set_ylabel("variation / nominal")
    ax2.set_yticks([0.5, 0.75, 1.0, 1.25, 1.5])
    ax2.set_yticklabels([0.5, 0.75, 1.0, 1.25, ""])
    ax2.tick_params(axis="both", which="major", pad=8)
    ax2.tick_params(direction="in", top=True, right=True, which="both")

    fig.tight_layout()

    utils._save_figure(fig, figure_path, close_figure)