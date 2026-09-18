import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tick.hawkes import HawkesExpKern

def slice_timestamps(timestamps, start_time, end_time):
    """
    Slices the timestamp arrays for a specific time window and
    re-zeros the epoch so the Hawkes learner doesn't fail on large offsets.
    """
    sliced_streams = []
    for t_stream in timestamps:
        # Extract events within the window
        mask = (t_stream >= start_time) & (t_stream < end_time)
        window_events = t_stream[mask]

        # Re-zero to the start of the window
        if len(window_events) > 0:
            window_events = window_events - start_time

        sliced_streams.append(window_events)
    return sliced_streams

def run_rolling_hawkes(timestamps, window_size_sec, step_size_sec, beta=2.0):
    """
    Fits the Hawkes model over rolling windows to track how market
    microstructure parameters evolve throughout the trading day.

    Args:
        timestamps: list of np.ndarray [news_times, price_times]
        window_size_sec: The width of the rolling window in seconds.
        step_size_sec: How far to step forward for the next window.
        beta: The fixed decay parameter (usually derived from a full-day grid search).

    Returns:
        pd.DataFrame containing the timeseries of fitted parameters.
    """
    # Find the absolute start and end times across all streams
    t_start = min([t[0] for t in timestamps if len(t) > 0])
    t_end = max([t[-1] for t in timestamps if len(t) > 0])

    results = []
    current_start = t_start

    print(f"Starting rolling fit: {int((t_end - t_start) / step_size_sec)} windows to process...")

    while current_start + window_size_sec <= t_end:
        current_end = current_start + window_size_sec
        window_streams = slice_timestamps(timestamps, current_start, current_end)

        # Require a minimum number of events to ensure a stable numerical fit
        num_news = len(window_streams[0])
        num_price = len(window_streams[1])

        if num_news > 2 and num_price > 50:
            try:
                learner = HawkesExpKern(decays=beta, penalty='l2', C=1e4)
                learner.fit(window_streams)

                alpha = learner.adjacency
                eigenvalues, _ = np.linalg.eig(alpha)
                endogeneity = np.max(np.abs(eigenvalues))

                results.append({
                    'window_start': current_start,
                    'window_end': current_end,
                    'news_count': num_news,
                    'price_count': num_price,
                    'baseline_news': learner.baseline[0],
                    'baseline_price': learner.baseline[1],
                    'alpha_news_to_price': alpha[1, 0],
                    'alpha_price_to_price': alpha[1, 1],
                    'endogeneity': endogeneity
                })
            except Exception as e:
                print(f"Fit failed at window {current_start}-{current_end}: {e}")

        current_start += step_size_sec

    return pd.DataFrame(results)

def plot_parameter_stability(rolling_df, save_path=None):
    """
    Visualizes the evolution of the News-to-Price impact and overall
    Market Endogeneity over time.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Plot 1: Endogeneity (Reflexivity)
    ax1.plot(rolling_df['window_start'], rolling_df['endogeneity'],
             color='#9467bd', linewidth=2, marker='o', markersize=4)
    ax1.axhline(1.0, color='red', linestyle='--', alpha=0.5, label='Critical Threshold (Explosive)')
    ax1.set_title("Market Endogeneity (Spectral Radius) Over Time", fontsize=12, fontweight='bold')
    ax1.set_ylabel("Endogeneity Ratio")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # Plot 2: News Impact Kernel
    ax2.plot(rolling_df['window_start'], rolling_df['alpha_news_to_price'],
             color='#ff7f0e', linewidth=2, marker='s', markersize=4)
    ax2.set_title("News-to-Price Impact ($\\alpha_{1,0}$) Over Time", fontsize=12, fontweight='bold')
    ax2.set_ylabel("Impact Magnitude")
    ax2.set_xlabel("Time (Seconds from Market Open)")
    ax2.grid(True, alpha=0.3)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved rolling stability plot to {save_path}")
    plt.show()

# ==========================================
# USAGE EXAMPLE
# ==========================================
if __name__ == "__main__":
    try:
        # Assuming `timestamps` and `best_beta` exist from the main fit script
        # 1-hour windows (3600 seconds), rolling forward every 15 minutes (900 seconds)
        print("Running dynamic Hawkes analysis...")
        rolling_results = run_rolling_hawkes(
            timestamps=timestamps,
            window_size_sec=3600,
            step_size_sec=900,
            beta=best_beta
        )

        print("\nRolling Analysis Snapshot:")
        print(rolling_results[['window_start', 'alpha_news_to_price', 'endogeneity']].head())

        plot_parameter_stability(rolling_results, save_path="rolling_hawkes_parameters.png")

    except NameError:
        print("Run the data generation from hawkes_fit.py first to populate the `timestamps` array.")
