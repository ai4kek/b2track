#!/usr/bin/env python3

"""
Belle II Tracking Parameter Analysis

This script analyzes the results of grid search optimization from run_scipy_grid.py.
It merges worker metrics, extracts best results, and creates visualizations.
"""

import logging
from pathlib import Path

import pandas as pd

# Import utilities from src.scipy_opt_utils
from src.scipy_opt_utils import METRICS_FIELDS
from src.scipy_plot_utils import (
    ParameterPlotter,
    extract_best_results,
    extract_reference_results,
    merge_worker_metrics,
    plot_efficiency_vs_purity_f1,
    plot_efficiency_vs_purity_time,
)

# Set Matplotlib style for better visualization
# plt.style.use("seaborn-v0_8-darkgrid")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("analyze_metrics")


def main():
    """Main function to run the analysis."""
    metrics_all_path = Path("metrics_all.csv")

    # Merge worker metrics if metrics_all.csv does not exist
    if not metrics_all_path.exists():
        merge_worker_metrics(METRICS_FIELDS, "metrics_all.csv")

    # Load dataset
    try:
        df = pd.read_csv(metrics_all_path)
    except Exception as e:
        print(f"Error: Failed to load metrics: {e}")
        return

    # Extract best and reference results
    best_results = extract_best_results(df)
    ref_results = extract_reference_results(df, index=10)

    # Visualize
    plot_efficiency_vs_purity_f1(df, best_results, ref_results)
    plot_efficiency_vs_purity_time(df, best_results, ref_results)

    plotter = ParameterPlotter(df, best_results, ref_results)
    plotter.plot_heatmaps()
    plotter.plot_violinplots()


if __name__ == "__main__":
    main()
