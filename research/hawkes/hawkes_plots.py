import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats

def plot_exp1_qq(residuals, save_path=None):
    """
    Generates a Q-Q plot comparing the integrated conditional intensity
    (the residuals) against a theoretical Exponential(1) distribution.
    If the points fall on the 45-degree line, the Hawkes model is correctly specified.
    """
    fig, ax = plt.subplots(figsize=(8, 8))

    # Generate theoretical quantiles for Exp(1)
    stats.probplot(residuals, dist="expon", plot=ax)

    # Styling for professional repo output
    ax.set_title("Residual Diagnostics: Q-Q Plot vs Exp(1)", fontsize=14, fontweight='bold')
    ax.set_ylabel("Empirical Quantiles (Compensator Integrals)", fontsize=12)
    ax.set_xlabel("Theoretical Quantiles (Exponential)", fontsize=12)

    # The stats.probplot line is red by default, we'll keep it but clean up the grid
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved Q-Q plot to {save_path}")

    plt.show()


def plot_intensity_impulse(news_times, price_times, baseline_price, alpha_news_to_price, beta, time_window, save_path=None):
    """
    Plots the conditional intensity function \\lambda(t) for price jumps
    in a specific time window, demonstrating the impulse response immediately
    following a macro news event.

    In the exponential kernel parameterization used by `tick`,
    the jump size in intensity is alpha * beta.
    """
    t_start, t_end = time_window
    t_grid = np.linspace(t_start, t_end, 2000)
    intensity = np.ones_like(t_grid) * baseline_price

    # Filter events within the window for visualization
    window_news = news_times[(news_times >= t_start) & (news_times <= t_end)]
    window_price = price_times[(price_times >= t_start) & (price_times <= t_end)]

    # Calculate decaying intensity from news events
    for t_n in window_news:
        mask = t_grid >= t_n
        # tick's HawkesExpKern alpha is the L1 norm of the kernel.
        # The actual jump at t_n is alpha * beta.
        intensity[mask] += (alpha_news_to_price * beta) * np.exp(-beta * (t_grid[mask] - t_n))

    fig, ax = plt.subplots(figsize=(12, 5))

    # Plot continuous intensity
    ax.plot(t_grid, intensity, color='#d62728', linewidth=2, label="Conditional Intensity $\\lambda_{price}(t)$")

    # Plot discrete event ticks
    ax.scatter(window_news, np.zeros_like(window_news) + baseline_price * 0.5,
               marker='^', color='#2ca02c', s=150, zorder=5, label="Macro News Headline")

    ax.scatter(window_price, np.zeros_like(window_price) + baseline_price * 0.8,
               marker='|', color='#1b77b4', s=200, zorder=5, label="Price Jump")

    # Styling
    ax.set_title("Information Diffusion: Price Intensity Response to Macro News", fontsize=14, fontweight='bold')
    ax.set_ylabel("Intensity (Events / Second)", fontsize=12)
    ax.set_xlabel("Time (Seconds)", fontsize=12)
    ax.set_xlim(t_start, t_end)
    ax.legend(loc="upper right", frameon=True, edgecolor='black')
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved Intensity plot to {save_path}")

    plt.show()

# ==========================================
# USAGE EXAMPLE (Assuming variables from hawkes_fit.py are in memory)
# ==========================================
if __name__ == "__main__":
    try:
        # 1. Validate the fit with the Time-Change Theorem
        print("Generating Q-Q Plot for Exp(1) residuals...")
        plot_exp1_qq(price_residuals, save_path="qq_residuals_exp1.png")

        # 2. Visualize the impulse response
        # Find a time window that contains at least one news event to zoom in on
        sample_news_time = news_timestamps[10] if len(news_timestamps) > 10 else news_timestamps[0]
        window = [sample_news_time - 1.0, sample_news_time + 4.0] # 1 sec before, 4 secs after

        print(f"Generating Intensity Plot around t={sample_news_time}...")
        plot_intensity_impulse(
            news_times=news_timestamps,
            price_times=price_timestamps,
            baseline_price=best_model.baseline[1],
            alpha_news_to_price=alpha[1, 0],
            beta=best_beta,
            time_window=window,
            save_path="intensity_impulse_response.png"
        )
    except NameError:
        print("Run hawkes_fit.py first to generate the model variables and residuals.")
