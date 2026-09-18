import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from tick.hawkes import SimuHawkesExpKern, HawkesExpKern

# ==========================================
# 1. GENERATE SYNTHETIC DATA (News & Price)
# ==========================================
# Dimension 0: Macro News
# Dimension 1: Price Moves
# For the sake of the model, we simulate a mutually exciting process.

# True parameters for simulation
true_baseline = np.array([0.05, 0.1])  # Base arrival rates
true_adjacency = np.array([
    [0.1, 0.0],  # News excites news (0.1), Price excites news (0.0)
    [0.6, 0.2]   # News excites price (0.6 - strong!), Price excites price (0.2)
])
true_decays = 2.0  # beta

hawkes_sim = SimuHawkesExpKern(
    baseline=true_baseline,
    adjacency=true_adjacency,
    decays=true_decays,
    end_time=10000,
    verbose=False,
    seed=42
)
hawkes_sim.simulate()

# Extract timestamp streams
news_timestamps = hawkes_sim.timestamps[0]
price_timestamps = hawkes_sim.timestamps[1]
timestamps = [news_timestamps, price_timestamps]

print(f"Total News Events: {len(news_timestamps)}")
print(f"Total Price Jumps: {len(price_timestamps)}")

# ==========================================
# 2. FIT THE HAWKES EXPONENTIAL KERNEL
# ==========================================
# Note: HawkesExpKern in tick requires passing the decay (beta).
# In practice, you run a grid search over beta to maximize the log-likelihood.
# We'll use a fixed beta grid search to find the optimal decay.

best_score = -np.inf
best_beta = None
best_model = None

# Grid search for the optimal beta (decay)
beta_candidates = np.linspace(0.5, 5.0, 10)

for beta in beta_candidates:
    learner = HawkesExpKern(decays=beta, penalty='l2', C=1e4)
    learner.fit(timestamps)
    score = learner.score()

    if score > best_score:
        best_score = score
        best_beta = beta
        best_model = learner

print("\n--- MODEL FIT RESULTS ---")
print(f"Optimal Beta (decay) found: {best_beta:.4f}")
print("Estimated Baseline (mu):", best_model.baseline)
print("Estimated Adjacency Matrix (alpha):\n", best_model.adjacency)

# ==========================================
# 3. EXTRACT MICROSTRUCTURE METRICS
# ==========================================
alpha = best_model.adjacency
beta = best_beta

# A. News-to-Price Kernel (Alpha 1,0)
alpha_news_to_price = alpha[1, 0]
print(f"\nNews-to-Price Impact (Alpha_10): {alpha_news_to_price:.4f}")

# B. Absorption Speed (Half-life)
# Formula: ln(2) / beta
half_life = np.log(2) / beta
print(f"Information Absorption Half-Life: {half_life:.4f} seconds")

# C. Endogeneity Ratio
# In a Hawkes process, the endogeneity is measured by the spectral radius
# (largest eigenvalue) of the branching matrix (alpha / beta in the exponential case,
# though tick parameterizes alpha as the integral of the kernel, so the branching matrix IS alpha).
eigenvalues, _ = np.linalg.eig(alpha)
spectral_radius = np.max(np.abs(eigenvalues))
print(f"Endogeneity Ratio (Branching Ratio): {spectral_radius:.4f}")
if spectral_radius < 1:
    print(" -> The process is stationary (sub-critical).")
else:
    print(" -> The process is explosive (super-critical).")

# ==========================================
# 4. EXP(1) RESIDUAL TEST (Time-Change Theorem)
# ==========================================
# If the model is correct, the integral of the conditional intensity function
# between arrival times (the compensator) should be i.i.d. Exponential(1).

def compute_compensator(timestamps, baseline, alpha, beta, dim):
    """
    Computes the integrated intensity for a specific dimension.
    """
    t_dim = timestamps[dim]
    residuals = []

    for i in range(1, len(t_dim)):
        t_current = t_dim[i]
        t_prev = t_dim[i-1]

        # Baseline contribution
        integral = baseline[dim] * (t_current - t_prev)

        # Excitation contribution from all dimensions
        for j in range(len(timestamps)):
            # Find all events in dim j strictly before t_current
            past_events = timestamps[j][timestamps[j] < t_current]
            if len(past_events) > 0:
                # Integral of exponential kernel: alpha * (1 - e^(-beta * (t_current - t_j)))
                # Evaluated between t_prev and t_current

                # Contribution at t_current
                val_curr = np.sum(np.exp(-beta * (t_current - past_events)))
                # Contribution at t_prev (only for events before t_prev)
                past_events_prev = past_events[past_events < t_prev]
                val_prev = np.sum(np.exp(-beta * (t_prev - past_events_prev))) if len(past_events_prev) > 0 else 0

                integral += alpha[dim, j] * (val_curr - val_prev)

        residuals.append(integral)
    return np.array(residuals)

# Compute residuals for the Price dimension
price_residuals = compute_compensator(timestamps, best_model.baseline, alpha, beta, dim=1)

# Statistical Test: Are these residuals Exp(1)?
# We can use the Kolmogorov-Smirnov test against standard exponential
ks_stat, p_value = stats.kstest(price_residuals, 'expon')

print("\n--- EXP(1) RESIDUAL TEST ---")
print(f"KS Statistic: {ks_stat:.4f}")
print(f"p-value: {p_value:.4f}")
if p_value > 0.05:
    print(" -> Fail to reject the null hypothesis. The residuals follow Exp(1). The fit is real.")
else:
    print(" -> Reject the null hypothesis. The model may be misspecified.")
