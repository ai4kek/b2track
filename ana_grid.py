#!/usr/bin/env python3

"""
Belle II Tracking Parameter Analysis

This script analyzes the results of grid search optimization from run_scipy_grid.py.
It merges worker metrics, extracts best results, and creates visualizations.
"""

import logging
from pathlib import Path

import pandas as pd

from src.optimization_utils import METRICS_FIELDS
from src.plotting_utils import (
    ParameterPlotter,
    extract_best_results,
    extract_reference_results,
    merge_worker_metrics,
    plot_efficiency_vs_purity_f1,
    plot_efficiency_vs_purity_time,
)

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
    ref_results = extract_reference_results(df)

    # Plot efficiency vs purity
    plot_efficiency_vs_purity_f1(df, best_results, ref_results)
    plot_efficiency_vs_purity_time(df, best_results, ref_results)

    # Plot parameter violin plots and heatmaps
    plotter = ParameterPlotter(df, best_results, ref_results)
    plotter.plot_violinplots()
    plotter.plot_heatmaps()


if __name__ == "__main__":
    main()
