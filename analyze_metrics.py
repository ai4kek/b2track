#!/usr/bin/env python3

"""
Belle II Tracking Parameter Analysis

This script analyzes the results of grid search optimization from run_scipy_grid.py.
It merges worker metrics, extracts best results, and creates visualizations.
"""

import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Import utilities from src.scipy_opt_utils
from src.scipy_opt_utils import (
    METRICS_FIELDS,
    extract_best_results,
    merge_worker_metrics,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("analyze_metrics")


def analyze_and_visualize(metrics_file="metrics_all.csv", best_results=None):
    """Analyze metrics and create visualizations with best result highlighted.

    Args:
        metrics_file: Path to the metrics CSV file
        best_results: Dictionary containing the best results (optional)
    """
    # Load the data
    try:
        # Read CSV file
        df = pd.read_csv(metrics_file)
    except Exception as e:
        logger.error(f"Error loading metrics file {metrics_file}: {e}")
        return

    # Calculate harmonic mean (F1 score) if not already present
    if "f1" not in df.columns:
        df["f1"] = (
            2 * (df["efficiency"] * df["purity"]) / (df["efficiency"] + df["purity"])
        )

    # Print best results if available
    if best_results:
        best_metrics = best_results["metrics"]
        print("\n=== Best Result ===")
        print(f"F1 Score: {best_metrics['f1']:.4f}")
        print(f"Efficiency: {best_metrics['efficiency']:.4f}")
        print(f"Purity: {best_metrics['purity']:.4f}")
        print("Parameters:")
        for param, value in best_results["parameters"].items():
            print(f"  {param}: {value}")

    # Create plots
    plot_efficiency_vs_purity_f1(df, best_results)
    plot_efficiency_vs_purity_time(df)

    # Create parameter heatmaps if we have enough data points
    create_parameter_plots(df, best_results)


def plot_efficiency_vs_purity_f1(df, best_results=None):
    """Plot efficiency vs purity with F1 score as colormap."""
    # Extract columns and create clean dataframe
    plot_df = pd.DataFrame(
        {
            "efficiency": pd.to_numeric(df["efficiency"], errors="coerce"),
            "purity": pd.to_numeric(df["purity"], errors="coerce"),
            "f1": pd.to_numeric(df["f1"], errors="coerce"),
        }
    ).dropna()

    # Create figure and axes
    fig, ax = plt.subplots(figsize=(10, 8))

    # Create colormap for F1 scores
    norm = plt.Normalize(plot_df["f1"].min(), plot_df["f1"].max())
    cmap = sns.color_palette("flare", as_cmap=True)

    # Create scatter plot
    sns.scatterplot(
        data=plot_df,
        x="efficiency",
        y="purity",
        hue="f1",
        size="f1",
        sizes=(20, 200),
        palette="flare",
        alpha=0.7,
        hue_norm=norm,
        ax=ax,
    )

    # Highlight best result if available
    if best_results:
        best_metrics = best_results["metrics"]
        best_point = (best_metrics["efficiency"], best_metrics["purity"])
        ax.scatter(
            best_point[0],
            best_point[1],
            s=200,
            color="red",
            marker="*",
            edgecolor="black",
            linewidth=1.5,
            label="Best Result",
        )

        # Add annotation
        ax.annotate(
            f"Best F1: {best_metrics['f1']:.4f}",
            xy=best_point,
            xytext=(10, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", alpha=0.8),
        )

    # Customize plot
    ax.set_title("Tracking Efficiency vs Purity (F1 Score)")
    ax.set_xlabel("Efficiency")
    ax.set_ylabel("Purity")
    ax.grid(True, alpha=0.3)
    fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), ax=ax, label="F1 Score")
    ax.legend()
    fig.tight_layout()

    # Save and close
    plt.savefig("efficiency_vs_purity_f1.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_efficiency_vs_purity_time(df):
    """Plot efficiency vs purity with execution time as colormap."""
    # Extract columns and create clean dataframe
    plot_df = pd.DataFrame(
        {
            "efficiency": pd.to_numeric(df["efficiency"], errors="coerce"),
            "purity": pd.to_numeric(df["purity"], errors="coerce"),
            "execution_time": pd.to_numeric(df["execution_time"], errors="coerce"),
        }
    ).dropna()

    # Create figure and axes
    fig, ax = plt.subplots(figsize=(10, 8))

    # Create colormap for execution time
    norm = plt.Normalize(
        plot_df["execution_time"].min(), plot_df["execution_time"].max()
    )
    cmap = sns.color_palette("viridis", as_cmap=True)

    # Create scatter plot
    sns.scatterplot(
        data=plot_df,
        x="efficiency",
        y="purity",
        hue="execution_time",
        size="execution_time",
        sizes=(20, 200),
        palette="viridis",
        alpha=0.7,
        hue_norm=norm,
        ax=ax,
    )

    # Customize plot
    ax.set_title("Tracking Efficiency vs Purity (Execution Time)")
    ax.set_xlabel("Efficiency")
    ax.set_ylabel("Purity")
    ax.grid(True, alpha=0.3)
    fig.colorbar(
        plt.cm.ScalarMappable(cmap=cmap, norm=norm), ax=ax, label="Execution Time (s)"
    )
    ax.legend()
    fig.tight_layout()

    # Save and close
    plt.savefig("efficiency_vs_purity_time.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def create_parameter_plots(df, best_results=None):
    """Create parameter distribution plots and heatmaps.

    Args:
        df: DataFrame containing the metrics data
        best_results: Dictionary containing the best results (optional)
    """
    param_columns = [
        col
        for col in df.columns
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

    if len(param_columns) >= 2 and len(df) >= 4:
        # Create parameter pair heatmaps for F1 score
        for i, param1 in enumerate(param_columns[:-1]):
            for param2 in param_columns[i + 1 :]:
                try:
                    # Skip if either parameter has only one unique value
                    if df[param1].nunique() <= 1 or df[param2].nunique() <= 1:
                        continue

                    plt.figure(figsize=(10, 8))
                    # Extract columns by name and convert to numeric
                    param1_values = pd.to_numeric(df[param1], errors="coerce")
                    param2_values = pd.to_numeric(df[param2], errors="coerce")
                    f1_values = pd.to_numeric(df["f1"], errors="coerce")

                    # Create a clean dataframe for pivoting
                    param1_values = sorted(df[param1].unique())
                    param2_values = sorted(df[param2].unique())
                    f1_matrix = np.zeros((len(param1_values), len(param2_values)))

                    # Fill the matrix with mean F1 scores
                    for i, p1 in enumerate(param1_values):
                        for j, p2 in enumerate(param2_values):
                            f1_matrix[i, j] = df[
                                (df[param1] == p1) & (df[param2] == p2)
                            ]["f1"].mean()

                    pivot = pd.DataFrame(
                        f1_matrix, index=param1_values, columns=param2_values
                    )

                    sns.heatmap(
                        pivot,
                        cmap="rocket",
                        annot=True,
                        fmt=".3f",
                        cbar_kws={"label": "F1 Score"},
                    )

                    # Mark best parameters if available
                    if (
                        best_results
                        and param1 in best_results["parameters"]
                        and param2 in best_results["parameters"]
                    ):
                        best_param1 = float(best_results["parameters"][param1])
                        best_param2 = float(best_results["parameters"][param2])

                        # Find the closest indices in the pivot table
                        # Ensure index and columns are numeric
                        idx1 = np.abs(np.array(pivot.index) - best_param1).argmin()
                        idx2 = np.abs(np.array(pivot.columns) - best_param2).argmin()

                        # Highlight the best cell
                        plt.scatter(
                            idx2 + 0.5,  # +0.5 to center in the heatmap cell
                            idx1 + 0.5,
                            s=200,
                            marker="*",
                            color="red",
                            edgecolor="white",
                            linewidth=1.5,
                            zorder=10,
                        )

                    plt.title(f"F1 Score Heatmap: {param1} vs {param2}")
                    plt.tight_layout()
                    plt.savefig(f"heatmap_{param1}_vs_{param2}.png", dpi=300)
                    plt.close()
                except Exception as e:
                    logger.warning(
                        f"Could not create heatmap for {param1} vs {param2}: {e}"
                    )

    # Create parameter distribution plots
    if len(df) > 1:
        for param in param_columns:
            try:
                plt.figure(figsize=(10, 6))

                # Extract columns by name and convert to numeric
                param_values = pd.to_numeric(df[param], errors="coerce")
                f1_values = pd.to_numeric(df["f1"], errors="coerce")

                # Create a clean dataframe for plotting
                plot_df = pd.DataFrame({param: param_values, "f1": f1_values}).dropna()

                # Create a categorical order based on sorted numeric values
                param_sorted = sorted(plot_df[param].unique())

                # Create violin plot with points
                sns.violinplot(
                    x=param,
                    y="f1",
                    data=plot_df,
                    inner=None,
                    color="lightgray",
                    order=param_sorted,  # Specify order to avoid categorical warnings
                )

                # Fix stripplot to avoid FutureWarning
                sns.stripplot(
                    x=param,
                    y="f1",
                    data=plot_df,
                    size=8,
                    alpha=0.6,
                    color="navy",  # Use fixed color instead of palette
                    order=param_sorted,  # Specify order to avoid categorical warnings
                )

                # Highlight best parameter if available
                if best_results and param in best_results["parameters"]:
                    best_param = float(best_results["parameters"][param])
                    best_f1 = best_results["metrics"]["f1"]

                    # Find the position of the best parameter value in the plot
                    # Use the position in the sorted unique values
                    if best_param in param_sorted:
                        param_pos = param_sorted.index(best_param)
                        plt.scatter(
                            [param_pos],
                            [best_f1],
                            s=200,
                            marker="*",
                            color="red",
                            edgecolor="black",
                            linewidth=1.5,
                            zorder=10,
                            label="Best Result",
                        )

                plt.title(f"F1 Score Distribution by {param}")
                plt.xlabel(param)
                plt.ylabel("F1 Score")
                plt.grid(True, axis="y", alpha=0.3)
                plt.legend()
                plt.tight_layout()
                plt.savefig(f"distribution_{param}.png", dpi=300)
                plt.close()
            except Exception as e:
                logger.warning(f"Could not create distribution plot for {param}: {e}")


def main():
    """Main function to run the analysis."""
    metrics_all_path = Path("metrics_all.csv")

    # Check if metrics_all.csv already exists
    if not metrics_all_path.exists():
        # If not, try to merge worker metrics files
        logger.info(
            "metrics_all.csv not found. Attempting to merge worker metrics files..."
        )
        merge_success = merge_worker_metrics(METRICS_FIELDS, "metrics_all.csv")

        if not merge_success:
            logger.error(
                "Could not find or merge any worker metrics files. Cannot proceed with analysis."
            )
            return
        logger.info("Successfully created metrics_all.csv from worker files")
    else:
        logger.info("Found existing metrics_all.csv file. Using it for analysis.")

    # Extract best results
    logger.info("Extracting best results from metrics_all.csv...")
    best_results = extract_best_results("metrics_all.csv")

    if best_results:
        # Save best results to JSON
        with open("best_results.json", "w") as f:
            json.dump(best_results, f, indent=2)

        logger.info("Best results saved to best_results.json")
        logger.info(f"🏆 Best F1 Score: {best_results['metrics']['f1']:.4f}")

        # Analyze and visualize
        logger.info("Analyzing and visualizing results...")
        analyze_and_visualize("metrics_all.csv", best_results)
    else:
        logger.warning(
            "No valid results found in metrics_all.csv. Cannot proceed with analysis."
        )
        return


if __name__ == "__main__":
    main()
