#!/usr/bin/env python3

"""
Belle II Tracking Parameter Analysis

This script analyzes the results of grid search optimization from run_scipy_grid.py.
It merges worker metrics, extracts best results, and creates visualizations.
"""
import csv
import json
import logging
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.optimization_utils import REF_PARAM

# Set Matplotlib style for better visualization
# plt.style.use("seaborn-v0_8-darkgrid")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("analyze_metrics")


def merge_worker_metrics(metrics_fields, output_file="metrics_all.csv"):
    """Merge all worker metrics files into a single metrics.csv, sorted by worker and trial.

    Handles missing or incomplete files gracefully. If a file cannot be read or
    is missing expected columns, it will be skipped with a warning.

    Args:
        metrics_fields: List of field names for the CSV
        output_file: Path to the output merged file

    Returns:
        bool: True if at least one row was merged, False otherwise
    """
    all_rows = []
    worker_files = sorted(Path().glob("metrics_worker_*.csv"))

    if not worker_files:
        logger.warning("No worker metrics files found to merge")
        return False

    for worker_file in worker_files:
        try:
            with worker_file.open() as f:
                reader = csv.DictReader(f)

                # Verify the file has the expected structure
                if not set(metrics_fields).issubset(set(reader.fieldnames or [])):
                    logger.warning(
                        f"Skipping {worker_file}: missing required columns")
                    continue

                file_rows = list(reader)
                if not file_rows:
                    logger.warning(
                        f"Skipping {worker_file}: file is empty or has only header"
                    )
                    continue

                all_rows.extend(file_rows)
                logger.info(f"Merged {len(file_rows)} rows from {worker_file}")
        except Exception as e:
            logger.warning(f"Error reading {worker_file}: {e}")
            continue

    if not all_rows:
        logger.warning("No valid rows found in any worker metrics files")
        return False

    # Sort by worker_id and trial_number if present
    all_rows.sort(
        key=lambda x: (int(x.get("worker_id", 0)),
                       int(x.get("trial_number", 0)))
    )

    with Path(output_file).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metrics_fields)
        writer.writeheader()
        writer.writerows(all_rows)

    logger.info(f"Successfully merged {len(all_rows)} rows into {output_file}")


def extract_results_from_row(row):
    """Extract parameters, metrics, and execution info from a DataFrame row or dict."""
    param_fields = [
        f
        for f in row.index
        if f
        not in [
            "efficiency",
            "purity",
            "f1",
            "finalstate",
            "execution_time",
            "worker_id",
            "trial_number",
        ]
    ]
    return {
        "parameters": {k: row[k] for k in param_fields},
        "metrics": {
            "f1": float(row.get("f1", 0)),
            "efficiency": float(row.get("efficiency", 0)),
            "purity": float(row.get("purity", 0)),
            "finalstate": row.get("finalstate", ""),
        },
        "execution": {
            "worker_id": int(row.get("worker_id", 0)),
            "trial_number": int(row.get("trial_number", 0)),
            "execution_time": float(row.get("execution_time", 0)),
        },
    }


def to_string_dict(obj):
    if isinstance(obj, dict):
        return {str(k): to_string_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_string_dict(v) for v in obj]
    else:
        return str(obj)


def extract_best_results(df):
    """Extract the best results (highest F1) from the DataFrame and save to JSON."""
    logger.info("Extracting best results from DataFrame")

    df_valid = df[pd.to_numeric(df["f1"], errors="coerce") >= 0].copy()
    if df_valid.empty:
        logger.warning("No valid rows with F1 scores found in DataFrame")
        return None

    # Find the row with the highest F1 score
    best_row = df_valid.loc[df_valid["f1"].idxmax()]
    result = extract_results_from_row(best_row)

    # Save to JSON
    with open("best_results.json", "w") as f:
        json.dump(to_string_dict(result), f, indent=2)

    return result


def extract_reference_results(df):
    """Extract the reference results (matching REF_PARAM) from the DataFrame and save to JSON."""
    logger.info("Extracting reference results from DataFrame using REF_PARAM")
    # Build a mask for all parameter columns
    mask = pd.Series([True] * len(df))
    for param, val in REF_PARAM.items():
        # Use == for numeric and object types (should match CSV typing)
        mask &= df[param] == val

    df_match = df[mask]

    if df_match.empty:
        logger.warning(
            f"No row found in DataFrame matching REF_PARAM: {REF_PARAM}")
        return None

    # Use the first matching row
    ref_row = df_match.iloc[0]
    result = extract_results_from_row(ref_row)

    # Save to JSON
    with open("ref_results.json", "w") as f:
        json.dump(to_string_dict(result), f, indent=2)

    return result


def plot_efficiency_vs_purity_f1(df, best_results=None, ref_results=None):
    """
    Plot efficiency vs purity, colored by F1.
    Mark best result with red star and annotate with F1.
    Mark reference result with blue square and annotate with F1.
    """

    logger.info("Plotting efficiency vs purity (F1 colormap)...")

    plot_df = pd.DataFrame(
        {
            "efficiency": pd.to_numeric(df["efficiency"], errors="coerce"),
            "purity": pd.to_numeric(df["purity"], errors="coerce"),
            "f1": pd.to_numeric(df["f1"], errors="coerce"),
        }
    ).dropna()

    fig, ax = plt.subplots(figsize=(10, 8))

    norm = plt.Normalize(plot_df["f1"].min(), plot_df["f1"].max())
    cmap = plt.get_cmap("plasma")

    sc = ax.scatter(
        plot_df["efficiency"],
        plot_df["purity"],
        c=plot_df["f1"],
        cmap=cmap,
        norm=norm,
        s=50,
        alpha=0.6,
        label=None,
    )

    # Best result (red circle)
    if best_results is not None:
        best = best_results["metrics"]
        best_execution = best_results["execution"]
        ax.scatter(
            [best["efficiency"]],
            [best["purity"]],
            s=100,
            facecolors="none",
            edgecolors="red",
            linewidths=2,
            zorder=11,
            label=f"Best (f1: {best['f1']:.3f}, t: {best_execution['execution_time']:.2f}s)",
        )
        ax.annotate(
            f"f1: {best['f1']:.3f}",
            (best["efficiency"], best["purity"]),
            xytext=(-50, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3",
                      fc="white", ec="red", alpha=0.8),
            color="red",
        )

    # Reference result (blue circle)
    if ref_results is not None:
        ref = ref_results["metrics"]
        ref_execution = ref_results["execution"]
        ax.scatter(
            [ref["efficiency"]],
            [ref["purity"]],
            s=100,
            facecolors="none",
            edgecolors="blue",
            linewidths=2,
            zorder=11,
            label=f"Reference (f1: {ref['f1']:.3f}, t: {ref_execution['execution_time']:.2f}s)",
        )
        ax.annotate(
            f"f1: {ref['f1']:.3f}",
            (ref["efficiency"], ref["purity"]),
            xytext=(-50, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3",
                      fc="white", ec="blue", alpha=0.8),
            color="blue",
        )

    ax.set_title("Hit Efficiency vs Hit Purity (F1 Score)")
    ax.set_xlabel("Efficiency")
    ax.set_ylabel("Purity")
    ax.grid(True, alpha=0.3)
    fig.colorbar(sc, ax=ax, label="F1 Score")
    ax.legend()
    fig.tight_layout()
    fig.savefig("efficiency_vs_purity_f1.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_efficiency_vs_purity_time(df, best_results=None, ref_results=None):
    """
    Plot efficiency vs purity, colored by execution time.
    Mark best result with red circle and annotate with execution time.
    Mark reference result with blue circle and annotate with execution time.
    """
    logger.info("Plotting efficiency vs purity (Time colormap)...")

    plot_df = pd.DataFrame(
        {
            "efficiency": pd.to_numeric(df["efficiency"], errors="coerce"),
            "purity": pd.to_numeric(df["purity"], errors="coerce"),
            "execution_time": pd.to_numeric(df["execution_time"], errors="coerce"),
        }
    ).dropna()

    fig, ax = plt.subplots(figsize=(10, 8))

    norm = plt.Normalize(
        plot_df["execution_time"].min(), plot_df["execution_time"].max()
    )
    cmap = plt.get_cmap("plasma")

    sc = ax.scatter(
        plot_df["efficiency"],
        plot_df["purity"],
        c=plot_df["execution_time"],
        cmap=cmap,
        norm=norm,
        s=50,
        alpha=0.6,
        label=None,
    )

    # Best result (red circle)
    if best_results is not None:
        best = best_results["execution"] if "execution" in best_results else {}
        metrics = best_results.get("metrics", {})
        if metrics and best:
            ax.scatter(
                [metrics["efficiency"]],
                [metrics["purity"]],
                s=100,
                facecolors="none",
                edgecolors="red",
                linewidths=2,
                zorder=11,
                label=f"Best (time: {best['execution_time']:.2f}s)",
            )
            ax.annotate(
                f"t: {best['execution_time']:.2f}s",
                (metrics["efficiency"], metrics["purity"]),
                xytext=(-50, 10),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.3",
                          fc="white", ec="red", alpha=0.8),
                color="red",
            )

    # Reference result (blue circle)
    if ref_results is not None:
        ref = ref_results["execution"] if "execution" in ref_results else {}
        metrics = ref_results["metrics"]
        ax.scatter(
            [metrics["efficiency"]],
            [metrics["purity"]],
            s=100,
            facecolors="none",
            edgecolors="blue",
            linewidths=2,
            zorder=11,
            label=f"Reference (time: {ref['execution_time']:.2f}s)",
        )
        ax.annotate(
            f"t: {ref['execution_time']:.2f}s",
            (metrics["efficiency"], metrics["purity"]),
            xytext=(-50, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3",
                      fc="white", ec="blue", alpha=0.8),
            color="blue",
        )

    ax.set_title("Hit Efficiency vs Hit Purity (Execution Time)")
    ax.set_xlabel("Efficiency")
    ax.set_ylabel("Purity")
    ax.grid(True, alpha=0.3)
    fig.colorbar(sc, ax=ax, label="Execution Time (s)")
    ax.legend()
    fig.tight_layout()
    fig.savefig("efficiency_vs_purity_time.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


class ParameterPlotter:
    def __init__(self, df, best_results=None, ref_results=None):
        self.df = df.copy()
        self.best_results = best_results
        self.ref_results = ref_results
        self.param_columns = [
            col
            for col in self.df.columns
            if col
            not in [
                "efficiency",
                "purity",
                "f1",
                "finalstate",
                "execution_time",
                "worker_id",
                "trial_number",
            ]
        ]

    def plot_heatmaps(self, save_dir="."):
        """
        Create pairwise parameter F1 heatmaps using Seaborn, marking best and reference results if provided.
        """
        logger.info("Plotting heatmaps...")
        os.makedirs(save_dir, exist_ok=True)
        if len(self.param_columns) >= 2 and len(self.df) >= 4:
            for i, param1 in enumerate(self.param_columns[:-1]):
                for param2 in self.param_columns[i + 1:]:
                    try:
                        if (
                            self.df[param1].nunique() <= 1
                            or self.df[param2].nunique() <= 1
                        ):
                            continue
                        pivot = self.df.pivot_table(
                            index=param1, columns=param2, values="f1", aggfunc="mean"
                        )
                        fig, ax = plt.subplots(figsize=(10, 8))
                        sns.heatmap(
                            pivot,
                            annot=True,
                            fmt=".3f",
                            cmap="plasma",
                            cbar_kws={"label": "F1 score"},
                            linewidths=0.5,
                            square=True,
                        )

                        # Mark best and reference results
                        def mark(ax, result, color, marker, label):
                            if result is None:
                                return
                            params = result.get("parameters", {})
                            x = params.get(param2, None)
                            y = params.get(param1, None)
                            if x is not None and y is not None:
                                try:
                                    # Find the cell coordinates
                                    xvals = list(pivot.columns)
                                    yvals = list(pivot.index)
                                    xi = (
                                        xvals.index(float(x))
                                        if float(x) in xvals
                                        else None
                                    )
                                    yi = (
                                        yvals.index(float(y))
                                        if float(y) in yvals
                                        else None
                                    )
                                    if xi is not None and yi is not None:
                                        ax.scatter(
                                            xi + 0.5,
                                            yi + 0.4,
                                            s=100,
                                            marker=marker,
                                            color=color,
                                            edgecolor=(
                                                "darkred" if color == "red" else "navy"
                                            ),
                                            linewidth=2,
                                            zorder=10,
                                            label=label,
                                            alpha=0.7 if color == "red" else 0.5,
                                        )
                                except Exception:
                                    pass

                        mark(ax, self.best_results, "red", "*", "Best")
                        mark(ax, self.ref_results, "blue", "o", "Reference")
                        ax.set_xlabel(param2)
                        ax.set_ylabel(param1)
                        ax.set_title(f"F1 Score Heatmap: {param1} vs {param2}")
                        handles, labels = ax.get_legend_handles_labels()
                        if handles:
                            ax.legend()
                        fig.tight_layout()
                        fig.savefig(
                            os.path.join(
                                save_dir, f"heatmap_{param1}_vs_{param2}.png"),
                            dpi=300,
                        )
                        plt.close(fig)
                    except Exception as e:
                        logger.warning(
                            f"Failed to plot heatmap for {param1} vs {param2}: {e}"
                        )

    def plot_violinplots(self, save_dir="."):
        """
        Create violin plots of F1 score by parameter using Seaborn, marking best and reference results if provided.
        """
        logger.info("Plotting violin plots...")

        os.makedirs(save_dir, exist_ok=True)
        for param in self.param_columns:
            try:
                plot_df = self.df[[param, "f1"]].dropna()
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.violinplot(
                    x=param, y="f1", data=plot_df, inner="quartile", color="lightgray"
                )
                # Overlay individual data points
                sns.stripplot(
                    x=param,
                    y="f1",
                    data=plot_df,
                    color="black",
                    size=4,
                    alpha=0.5,
                    ax=ax,
                    jitter=True,
                )

                # Mark best and reference results
                def mark(ax, result, color, marker, label):
                    if result and param in result.get("parameters", {}):
                        try:
                            val = float(result["parameters"][param])
                            f1 = float(result["metrics"]["f1"])
                            idx = list(
                                sorted(plot_df[param].unique())).index(val)
                            ax.scatter(
                                [idx],
                                [f1],
                                s=50,
                                marker=marker,
                                color=color,
                                edgecolor="darkred" if color == "red" else "navy",
                                linewidth=1.5,
                                zorder=10,
                                label=label,
                                alpha=0.7 if color == "red" else 0.5,
                            )
                        except Exception:
                            pass

                # Mark best result (red star) and reference (blue circle)
                mark(ax, self.best_results, "red", "*", "Best")
                mark(ax, self.ref_results, "blue", "o", "Reference")

                # Remove duplicate legend entries
                handles, labels = ax.get_legend_handles_labels()
                by_label = dict(zip(labels, handles))
                if by_label:
                    ax.legend(by_label.values(), by_label.keys())

                ax.set_title(f"F1 Score Distribution by {param}")
                ax.set_xlabel(param)
                ax.set_ylabel("F1 Score")
                plt.tight_layout()
                fig.savefig(
                    os.path.join(save_dir, f"violin_{param}_f1.png"),
                    dpi=300,
                    bbox_inches="tight",
                )
                plt.close(fig)
            except Exception as e:
                logger.warning(
                    f"Could not create violin plot for {param}: {e}")
