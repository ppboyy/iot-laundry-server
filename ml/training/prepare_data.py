#!/usr/bin/env python3
"""
STEP 1-3: Data Preparation Pipeline
- Load raw power data
- Apply Savitzky-Golay smoothing
- Extract features
- Generate rule-based labels
"""

import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from datetime import datetime
import os
import json

# Configuration
WINDOW_LENGTH = 11  # Savitzky-Golay window (~5.5 minutes at 30s intervals)
POLYORDER = 3       # Cubic polynomial
FEATURE_WINDOW = 4  # Number of samples for rolling features (2 minutes)

def load_raw_data(csv_path):
    """Load raw power consumption data from CSV"""
    print(f"📂 Loading data from {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Rename columns if needed
    if 'power_w' in df.columns:
        df.rename(columns={'power_w': 'power'}, inplace=True)
    
    # Parse timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['time_seconds'] = (df['timestamp'] - df['timestamp'].iloc[0]).dt.total_seconds()
    
    print(f"✅ Loaded {len(df)} samples")
    print(f"   Duration: {df['time_seconds'].iloc[-1] / 60:.1f} minutes")
    print(f"   Power range: {df['power'].min():.1f}W - {df['power'].max():.1f}W")
    
    return df

def apply_savgol_smoothing(df):
    """Apply Savitzky-Golay filter for ML-friendly smoothing"""
    print(f"\n🔧 Applying Savitzky-Golay filter (window={WINDOW_LENGTH}, poly={POLYORDER})")
    
    # Handle edge cases with mode='nearest'
    df['power_smooth'] = savgol_filter(
        df['power'], 
        window_length=WINDOW_LENGTH, 
        polyorder=POLYORDER,
        mode='nearest'
    )
    
    # Calculate smoothing improvement
    noise_before = df['power'].diff().abs().mean()
    noise_after = df['power_smooth'].diff().abs().mean()
    improvement = ((noise_before - noise_after) / noise_before) * 100
    
    print(f"✅ Smoothing complete")
    print(f"   Noise reduction: {improvement:.1f}%")
    
    return df

def extract_features(df):
    """Extract time-domain features for ML training"""
    print(f"\n🔍 Extracting features...")
    
    # Use smoothed power for feature extraction
    power = df['power_smooth']
    
    # Rolling statistics (using FEATURE_WINDOW)
    df['power_avg_30s'] = power.rolling(window=2, min_periods=1).mean()
    df['power_avg_60s'] = power.rolling(window=FEATURE_WINDOW, min_periods=1).mean()
    df['power_std_30s'] = power.rolling(window=2, min_periods=1).std().fillna(0)
    df['power_std_60s'] = power.rolling(window=FEATURE_WINDOW, min_periods=1).std().fillna(0)
    
    # Min/Max in window
    df['power_min_30s'] = power.rolling(window=2, min_periods=1).min()
    df['power_max_30s'] = power.rolling(window=2, min_periods=1).max()
    df['power_range_30s'] = df['power_max_30s'] - df['power_min_30s']
    
    # Derivative (rate of change)
    df['power_derivative'] = np.gradient(power)
    
    # Time in current power range (stability indicator)
    df['time_in_range'] = 0
    for i in range(len(df)):
        if i < FEATURE_WINDOW:
            df.loc[i, 'time_in_range'] = i
        else:
            recent = power.iloc[i-FEATURE_WINDOW:i+1]
            current = power.iloc[i]
            # Count samples within ±20W of current
            df.loc[i, 'time_in_range'] = sum(abs(recent - current) < 20)
    
    # Oscillation measure (how much power varies)
    df['power_oscillation'] = power.rolling(window=FEATURE_WINDOW, min_periods=1).apply(
        lambda x: (x.max() - x.min()) / (x.mean() + 1e-6)
    ).fillna(0)
    
    print(f"✅ Extracted features:")
    print(f"   - Rolling averages (30s, 60s)")
    print(f"   - Standard deviation (volatility)")
    print(f"   - Min/Max/Range in window")
    print(f"   - Power derivative (rate of change)")
    print(f"   - Time in range (stability)")
    print(f"   - Oscillation measure")
    
    return df

def label_phases_rule_based(df):
    """Generate phase labels using rule-based detection"""
    print(f"\n🏷️  Generating rule-based phase labels...")
    
    power = df['power_smooth']
    power_avg_60s = df['power_avg_60s']
    
    # Initialize labels
    labels = []
    
    # First pass: Basic labeling by power level
    for i in range(len(df)):
        p = power.iloc[i]
        p_avg = power_avg_60s.iloc[i]
        
        # Rule-based classification based on actual power graph pattern
        if p < 15:
            # Idle/Standby
            label = 'IDLE'
        elif p > 280 or p_avg > 250:
            # Sustained high power = SPIN
            label = 'SPIN'
        elif p > 220 or p_avg > 180:
            # Power spike above 220W OR average above 180W = RINSE
            # From your graph: washing stays mostly under 200W, rinse spikes much higher
            label = 'RINSE'
        elif p >= 15 and p < 220:
            # 15-220W = WASHING (the oscillating baseline)
            label = 'WASHING'
        else:
            label = 'WASHING'  # Default
        
        labels.append(label)
    
    df['phase'] = labels
    
    # Second pass: Expand RINSE windows
    # If we detect a rinse spike, mark surrounding samples as RINSE too
    labels = df['phase'].values.copy()
    window = 20  # Expand rinse detection by 20 samples (~3-4 minutes)
    
    for i in range(len(labels)):
        if labels[i] == 'RINSE':
            # Mark previous and next samples as RINSE
            start = max(0, i - window)
            end = min(len(labels), i + window)
            for j in range(start, end):
                if labels[j] == 'WASHING':
                    labels[j] = 'RINSE'
    
    df['phase'] = labels
    
    # Apply state machine constraints
    df = apply_state_machine_constraints(df)
    
    # Print label distribution
    print(f"✅ Phase label distribution:")
    for phase, count in df['phase'].value_counts().items():
        percentage = (count / len(df)) * 100
        duration = (count * 10) / 60  # Approximate minutes
        print(f"   {phase:12s}: {count:4d} samples ({percentage:5.1f}%) ~{duration:.1f} min")
    
    return df

def apply_state_machine_constraints(df):
    """Refine labels using washing machine cycle constraints"""
    print("   Applying state machine constraints...")
    
    phases = df['phase'].values
    
    # Constraint 1: Remove very short phases (noise)
    min_phase_length = 3  # At least 30 seconds
    i = 0
    while i < len(phases) - min_phase_length:
        current_phase = phases[i]
        # Find end of current phase
        j = i
        while j < len(phases) and phases[j] == current_phase:
            j += 1
        
        # If phase is too short and not IDLE, mark as previous phase
        if j - i < min_phase_length and current_phase not in ['IDLE']:
            if i > 0:
                phases[i:j] = phases[i-1]
        
        i = j if j > i else i + 1
    
    # Constraint 2: SPIN only occurs after WASHING/RINSE
    for i in range(1, len(phases)):
        if phases[i] == 'SPIN' and phases[i-1] not in ['WASHING', 'RINSE', 'SPIN']:
            # Probably a spike, not actual spin
            if df['power_smooth'].iloc[i] < 300:
                phases[i] = phases[i-1]
    
    df['phase'] = phases
    return df

def save_prepared_data(df, output_path):
    """Save prepared data with all features and labels"""
    print(f"\n💾 Saving prepared data to {output_path}")
    
    # Select feature columns for ML training
    feature_cols = [
        'timestamp', 'time_seconds',
        'power', 'power_smooth',
        'power_avg_30s', 'power_avg_60s',
        'power_std_30s', 'power_std_60s',
        'power_min_30s', 'power_max_30s', 'power_range_30s',
        'power_derivative', 'time_in_range', 'power_oscillation',
        'phase'
    ]
    
    df_output = df[feature_cols]
    df_output.to_csv(output_path, index=False)
    
    print(f"✅ Saved {len(df_output)} samples with {len(feature_cols)-1} features")
    
    # Save metadata
    metadata = {
        'samples': len(df_output),
        'duration_minutes': df['time_seconds'].iloc[-1] / 60,
        'features': [col for col in feature_cols if col not in ['timestamp', 'time_seconds', 'phase']],
        'phases': df['phase'].value_counts().to_dict(),
        'smoothing': {
            'method': 'savitzky_golay',
            'window_length': WINDOW_LENGTH,
            'polyorder': POLYORDER
        },
        'created_at': datetime.now().isoformat()
    }
    
    metadata_path = output_path.replace('.csv', '_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Saved metadata to {metadata_path}")

def main():
    """Main data preparation pipeline"""
    print("=" * 70)
    print("WASHING MACHINE ML - DATA PREPARATION PIPELINE")
    print("=" * 70)
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    input_csv = os.path.join(project_root, 'data', 'power_log_raw.csv')
    output_csv = os.path.join(project_root, 'data', 'power_log_prepared.csv')
    
    # Check if input exists
    if not os.path.exists(input_csv):
        print(f"❌ Input file not found: {input_csv}")
        print(f"   Please copy power_log_gus.csv to ml/data/power_log_raw.csv")
        return
    
    try:
        # Step 1: Load data
        df = load_raw_data(input_csv)
        
        # Step 2: Apply Savitzky-Golay smoothing
        df = apply_savgol_smoothing(df)
        
        # Step 3: Extract features
        df = extract_features(df)
        
        # Step 4: Generate labels
        df = label_phases_rule_based(df)
        
        # Step 5: Save prepared data
        save_prepared_data(df, output_csv)
        
        print("\n" + "=" * 70)
        print("✅ DATA PREPARATION COMPLETE!")
        print("=" * 70)
        print(f"\nNext steps:")
        print(f"1. Review prepared data: {output_csv}")
        print(f"2. Run training: python training/train_random_forest.py")
        print(f"3. Or train CNN: python training/train_cnn.py")
        
    except Exception as e:
        print(f"\n❌ Error during data preparation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
