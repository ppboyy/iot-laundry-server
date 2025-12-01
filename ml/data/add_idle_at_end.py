import pandas as pd
import numpy as np

# -----------------------------
# CONFIG
# -----------------------------
INPUT_CSV  = "power_log_prepared.csv"        # or "power_log_extended_idle.csv"
OUTPUT_CSV = "power_log_with_extra_idle.csv"

EXTRA_IDLE_SECONDS = 600   # 10 minutes of idle to append (change if needed)
TIME_IN_RANGE_IDLE = 5     # matches your existing IDLE rows

# -----------------------------
# 1. Load existing data
# -----------------------------
df = pd.read_csv(INPUT_CSV)

# Infer sampling interval from data (your data is ~10 s apart)
dt = df["time_seconds"].diff().median()
if pd.isna(dt) or dt <= 0:
    raise ValueError("Could not infer a positive sampling interval from time_seconds")

n_new = int(EXTRA_IDLE_SECONDS / dt)

print(f"Sampling interval ≈ {dt:.3f} s, adding {n_new} idle rows (~{EXTRA_IDLE_SECONDS} s).")

# -----------------------------
# 2. Learn idle power stats from existing IDLE rows (near the end)
# -----------------------------
idle_tail = df[df["phase"] == "IDLE"].tail(200)  # last 200 IDLE rows

if idle_tail.empty:
    # Fallback: use overall low-power region
    low_power = df[df["power"] < df["power"].quantile(0.1)]
    idle_mu = low_power["power"].mean()
    idle_sigma = low_power["power"].std()
else:
    idle_mu = idle_tail["power"].mean()
    idle_sigma = idle_tail["power"].std()

if np.isnan(idle_sigma) or idle_sigma == 0:
    idle_sigma = 0.3  # small noise if all identical

print(f"Idle power mean ≈ {idle_mu:.3f} W, std ≈ {idle_sigma:.3f} W")

# -----------------------------
# 3. Helper to format timestamp from time_seconds
#     (mm:ss.t format like '46:07.7')
# -----------------------------
def format_timestamp(t_sec: float) -> str:
    m = int(t_sec // 60)
    s = t_sec - 60 * m
    # one decimal place for seconds
    return f"{m:02d}:{s:04.1f}"

# -----------------------------
# 4. Generate new idle rows
# -----------------------------
last_time = df["time_seconds"].iloc[-1]

new_times = last_time + np.arange(1, n_new + 1) * dt
new_power = np.random.normal(loc=idle_mu, scale=idle_sigma, size=n_new)

# Small random “oscillation” term similar to your existing idle
new_osc = np.random.uniform(0.15, 0.7, size=n_new)

new_rows = pd.DataFrame({
    "timestamp":      [format_timestamp(t) for t in new_times],
    "time_seconds":   new_times,
    "power":          new_power,
    "power_smooth":   new_power,
    "power_avg_30s":  new_power,
    "power_avg_60s":  new_power,
    "power_std_30s":  np.zeros(n_new),
    "power_std_60s":  np.zeros(n_new),
    "power_min_30s":  new_power,
    "power_max_30s":  new_power,
    "power_range_30s": np.zeros(n_new),
    "power_derivative": np.zeros(n_new),
    "time_in_range":  np.full(n_new, TIME_IN_RANGE_IDLE),
    "power_oscillation": new_osc,
    "phase":          ["IDLE"] * n_new,
})

# -----------------------------
# 5. Append and save
# -----------------------------
df_extended = pd.concat([df, new_rows], ignore_index=True)
df_extended.to_csv(OUTPUT_CSV, index=False)

print(f"Done! Saved extended file as: {OUTPUT_CSV}")
print(f"Original rows: {len(df)}, new total: {len(df_extended)}")

