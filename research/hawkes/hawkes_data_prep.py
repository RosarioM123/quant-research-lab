import pandas as pd
import numpy as np

def load_and_filter_hours(df, time_col, start_hour='09:30', end_hour='16:00', tz='America/New_York'):
    """
    Ensures datetimes are localized and filters out after-hours data.
    Overnight gaps violate the Hawkes continuous-time assumption.
    """
    # Ensure datetime format
    if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
        df[time_col] = pd.to_datetime(df[time_col])

    # Localize timezone if naive, otherwise convert
    if df[time_col].dt.tz is None:
        df[time_col] = df[time_col].dt.tz_localize('UTC').dt.tz_convert(tz)
    else:
        df[time_col] = df[time_col].dt.tz_convert(tz)

    # Filter for standard trading hours
    df = df.set_index(time_col)
    df = df.between_time(start_hour, end_hour).copy()

    # Reset index to keep time as a column
    df = df.reset_index()
    return df

def generate_hawkes_streams(news_df, price_df, news_time_col='timestamp', price_time_col='timestamp'):
    """
    Takes raw news and price DataFrames and converts them into the
    list of 1D numpy arrays required by the `tick` library.

    Args:
        news_df: DataFrame containing macro news events.
        price_df: DataFrame containing price tick data.

    Returns:
        list of np.ndarray: [news_timestamps_sec, price_timestamps_sec]
    """
    print(f"Raw News Events: {len(news_df)} | Raw Price Ticks: {len(price_df)}")

    # 1. Clean and filter for market hours
    news_clean = load_and_filter_hours(news_df, news_time_col)
    price_clean = load_and_filter_hours(price_df, price_time_col)

    # 2. Extract price jumps only (filtering out zero-tick moves)
    # Assuming price_df has a 'price' column. We only want timestamps where price actually moved.
    if 'price' in price_clean.columns:
        price_clean['price_change'] = price_clean['price'].diff().fillna(0)
        price_jumps = price_clean[price_clean['price_change'] != 0].copy()
    else:
        # If already pre-filtered for jumps
        price_jumps = price_clean

    # 3. Establish a common T-zero (epoch)
    # To prevent float precision issues in Hawkes fitting, set the very first
    # event of the day (across both datasets) as t=0.0
    first_news = news_clean[news_time_col].min()
    first_price = price_jumps[price_time_col].min()
    epoch = min(first_news, first_price)

    print(f"Epoch set to: {epoch}")

    # 4. Convert datetimes to relative seconds (floats)
    news_clean['t_sec'] = (news_clean[news_time_col] - epoch).dt.total_seconds()
    price_jumps['t_sec'] = (price_jumps[price_time_col] - epoch).dt.total_seconds()

    # 5. Extract strictly increasing float arrays
    # Hawkes requires strictly positive inter-arrival times.
    # Add microscopic jitter to simultaneous timestamps if necessary.
    news_times = np.sort(news_clean['t_sec'].values)
    price_times = np.sort(price_jumps['t_sec'].values)

    # Function to resolve duplicate timestamps (sub-millisecond bursts)
    def resolve_duplicates(times):
        diffs = np.diff(times)
        while (diffs == 0).any():
            # Add 1 microsecond to the duplicate
            zero_idx = np.where(diffs == 0)[0]
            times[zero_idx + 1] += 1e-6
            diffs = np.diff(times)
        return times

    news_times = resolve_duplicates(news_times)
    price_times = resolve_duplicates(price_times)

    print(f"Final valid News events: {len(news_times)}")
    print(f"Final valid Price jumps: {len(price_times)}")

    return [news_times, price_times]

# ==========================================
# USAGE EXAMPLE
# ==========================================
if __name__ == "__main__":
    # Simulate loading real CSV data
    print("Simulating raw Bloomberg/Refinitiv data load...")

    # Mock News Data
    mock_news = pd.DataFrame({
        'timestamp': pd.date_range(start='2026-09-18 09:30:00', end='2026-09-18 16:00:00', freq='30min'),
        'headline': ['CPI Data', 'Fed Speak', 'Jobless Claims'] * 4 + ['Market Close']
    })

    # Mock Price Data (High Frequency)
    mock_price = pd.DataFrame({
        'timestamp': pd.date_range(start='2026-09-18 09:30:00', end='2026-09-18 16:00:00', freq='1s'),
        'price': np.random.randn(23401).cumsum() + 5000 # Random walk
    })

    # Generate the aligned arrays for hawkes_fit.py
    hawkes_input_streams = generate_hawkes_streams(mock_news, mock_price)

    # In a real workflow, you would save these to an .npz file or pass directly to the learner
    # np.savez('data/processed/aligned_streams.npz', news=hawkes_input_streams[0], price=hawkes_input_streams[1])
