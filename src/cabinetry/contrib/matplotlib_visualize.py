import logging
import os
from pathlib import Path
from typing import List

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


log = logging.getLogger(__name__)


def _total_yield_uncertainty(stdev_list):
    """calculate the absolute statistical uncertainty of a stack of MC
    via sum in quadrature

    Args:
        stdev_list (list): list of absolute stat. uncertainty per sample

    Returns:
        np.array: absolute stat. uncertainty of stack of samples
    """
    tot_unc = np.sqrt(np.sum(np.power(stdev_list, 2), axis=0))
    return tot_unc


def data_MC(histogram_dict_list, figure_path):
    """draw a data/MC histogram with matplotlib

    Args:
        histogram_dict_list (list[dict]): list of samples (with info stored in one dict per sample)
        figure_path (pathlib.Path): path where figure should be saved
    """
    mc_histograms_yields = []
    mc_histograms_stdev = []
    mc_labels = []
    for h in histogram_dict_list:
        if h["isData"]:
            data_histogram_yields = h["hist"]["yields"]
            data_histogram_stdev = h["hist"]["stdev"]
            data_label = h["label"]
        else:
            mc_histograms_yields.append(h["hist"]["yields"])
            mc_histograms_stdev.append(h["hist"]["stdev"])
            mc_labels.append(h["label"])

    # get the highest single bin from the sum of MC
    y_max = np.max(
        np.sum(
            [h["hist"]["yields"] for h in histogram_dict_list if not h["isData"]],
            axis=0,
        )
    )

    # if data is higher in any bin, the maximum y axis range should take that into account
    y_max = max(
        y_max, np.max([h["hist"]["yields"] for h in histogram_dict_list if h["isData"]])
    )

    mpl.style.use("seaborn-colorblind")
    fig, ax = plt.subplots()

    # plot MC stacked together
    total_yield = np.zeros_like(mc_histograms_yields[0])
    bins = histogram_dict_list[0]["hist"]["bins"]
    bin_right_edges = bins[1:]
    bin_left_edges = bins[:-1]
    bin_width = bin_right_edges - bin_left_edges
    bin_centers = 0.5 * (bin_left_edges + bin_right_edges)
    for i_sample, mc_sample_yield in enumerate(mc_histograms_yields):
        ax.bar(
            bin_centers,
            mc_sample_yield,
            width=bin_width,
            bottom=total_yield,
            label=mc_labels[i_sample],
        )
        total_yield += mc_sample_yield

    # add total MC uncertainty
    mc_stack_unc = _total_yield_uncertainty(mc_histograms_stdev)
    ax.bar(
        bin_centers,
        2 * mc_stack_unc,
        width=bin_width,
        bottom=total_yield - mc_stack_unc,
        label="Stat. uncertainty",
        fill=False,
        linewidth=0,
        edgecolor="gray",
        hatch=3 * "/",
    )

    # plot data
    ax.errorbar(
        bin_centers,
        data_histogram_yields,
        yerr=data_histogram_stdev,
        fmt="o",
        c="k",
        label=data_label,
    )

    ax.legend(frameon=False)
    ax.set_xlabel(histogram_dict_list[0]["variable"])
    ax.set_ylabel("events")
    ax.set_xlim(bin_left_edges[0], bin_right_edges[-1])
    ax.set_ylim([0, y_max * 1.1])  # 10% headroom

    if not os.path.exists(figure_path.parent):
        os.mkdir(figure_path.parent)
    log.debug(f"saving figure as {figure_path}")
    fig.savefig(figure_path)


def correlation_matrix(
    corr_mat: np.ndarray, labels: List[str], figure_path: Path
) -> None:
    """draw a correlation matrix

    Args:
        corr_mat (np.ndarray): the correlation matrix to plot
        labels (List[str]): names of parameters in the correlation matrix
        figure_path (pathlib.Path): path where figure should be saved
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr_mat, vmin=-1, vmax=1, cmap="RdBu")

    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    for tick in ax.get_xticklabels():
        tick.set_rotation(45)
        tick.set_horizontalalignment("right")

    fig.colorbar(im, ax=ax)
    ax.set_aspect("auto")  # to get colorbar aligned with matrix
    fig.tight_layout()

    # add correlation as text
    for (j, i), label in np.ndenumerate(corr_mat):
        if abs(corr_mat[j, i]) > 0.75:
            text_color = "white"
        else:
            text_color = "black"
        ax.text(i, j, f"{label:.2f}", ha="center", va="center", c=text_color)

    if not os.path.exists(figure_path.parent):
        os.mkdir(figure_path.parent)
    log.debug(f"saving figure as {figure_path}")
    fig.savefig(figure_path)