#!/usr/bin/env python3
"""
Test script to verify ML training pipeline is working correctly
Run this after setup to ensure everything is configured properly
"""

import os
import sys

def test_imports():
    """Test if all required packages are installed"""
    print("Testing package imports...")
    
    try:
        import numpy as np
        print("  ✅ numpy:", np.__version__)
    except ImportError as e:
        print(f"  ❌ numpy not found: {e}")
        return False
    
    try:
        import pandas as pd
        print("  ✅ pandas:", pd.__version__)
    except ImportError as e:
        print(f"  ❌ pandas not found: {e}")
        return False
    
    try:
        from scipy.signal import savgol_filter
        print("  ✅ scipy (Savitzky-Golay available)")
    except ImportError as e:
        print(f"  ❌ scipy not found: {e}")
        return False
    
    try:
        from sklearn.ensemble import RandomForestClassifier
        print("  ✅ scikit-learn available")
    except ImportError as e:
        print(f"  ❌ scikit-learn not found: {e}")
        return False
    
    try:
        import tensorflow as tf
        print("  ✅ tensorflow:", tf.__version__)
    except ImportError as e:
        print(f"  ⚠️  tensorflow not found (optional for CNN): {e}")
    
    try:
        import matplotlib
        print("  ✅ matplotlib available")
    except ImportError as e:
        print(f"  ⚠️  matplotlib not found (optional for visualization): {e}")
    
    return True

def test_data():
    """Test if training data is available"""
    print("\nTesting training data...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, 'data', 'power_log_raw.csv')
    
    if not os.path.exists(data_path):
        print(f"  ❌ Training data not found: {data_path}")
        print(f"     Please copy power_log_gus.csv to ml/data/power_log_raw.csv")
        return False
    
    # Try to load data
    try:
        import pandas as pd
        df = pd.read_csv(data_path)
        
        print(f"  ✅ Training data found: {len(df)} samples")
        
        # Check columns
        if 'power_w' in df.columns or 'power' in df.columns:
            print(f"  ✅ Power column present")
        else:
            print(f"  ❌ Power column not found in CSV")
            return False
        
        if 'timestamp' in df.columns:
            print(f"  ✅ Timestamp column present")
        else:
            print(f"  ⚠️  Timestamp column not found (optional)")
        
        # Check data range
        power_col = 'power_w' if 'power_w' in df.columns else 'power'
        power_min = df[power_col].min()
        power_max = df[power_col].max()
        
        print(f"  ✅ Power range: {power_min:.1f}W - {power_max:.1f}W")
        
        if power_max > 100:
            print(f"  ✅ Data includes washing cycle (high power detected)")
        else:
            print(f"  ⚠️  Data might be idle only (max power = {power_max:.1f}W)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error loading data: {e}")
        return False

def test_directories():
    """Test if required directories exist"""
    print("\nTesting directory structure...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    dirs = [
        ('data', True),
        ('models', True),
        ('training', True),
    ]
    
    all_exist = True
    for dir_name, required in dirs:
        dir_path = os.path.join(script_dir, dir_name)
        if os.path.exists(dir_path):
            print(f"  ✅ {dir_name}/ exists")
        else:
            if required:
                print(f"  ❌ {dir_name}/ not found (required)")
                all_exist = False
            else:
                print(f"  ⚠️  {dir_name}/ not found (optional)")
    
    return all_exist

def test_scripts():
    """Test if training scripts exist"""
    print("\nTesting training scripts...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    scripts = [
        'training/prepare_data.py',
        'training/train_random_forest.py',
        'training/train_cnn.py',
    ]
    
    all_exist = True
    for script in scripts:
        script_path = os.path.join(script_dir, script)
        if os.path.exists(script_path):
            print(f"  ✅ {script}")
        else:
            print(f"  ❌ {script} not found")
            all_exist = False
    
    return all_exist

def test_savgol_filter():
    """Test Savitzky-Golay filter with sample data"""
    print("\nTesting Savitzky-Golay filter...")
    
    try:
        import numpy as np
        from scipy.signal import savgol_filter
        
        # Create sample noisy data
        x = np.linspace(0, 10, 100)
        y = np.sin(x) + np.random.normal(0, 0.1, 100)
        
        # Apply filter
        y_smooth = savgol_filter(y, window_length=11, polyorder=3)
        
        # Check if smoothing worked
        noise_before = np.diff(y).std()
        noise_after = np.diff(y_smooth).std()
        
        if noise_after < noise_before:
            improvement = ((noise_before - noise_after) / noise_before) * 100
            print(f"  ✅ Savitzky-Golay filter working ({improvement:.1f}% noise reduction)")
            return True
        else:
            print(f"  ❌ Savitzky-Golay filter not reducing noise")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing filter: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 70)
    print("ML TRAINING PIPELINE - SYSTEM TEST")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Package Imports", test_imports()))
    results.append(("Directory Structure", test_directories()))
    results.append(("Training Scripts", test_scripts()))
    results.append(("Training Data", test_data()))
    results.append(("Savitzky-Golay Filter", test_savgol_filter()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:8s} - {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✅ All tests passed! System is ready for training.")
        print("\nNext steps:")
        print("1. python training/prepare_data.py")
        print("2. python training/train_random_forest.py")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix issues before training.")
        print("\nCommon fixes:")
        print("- Install packages: pip install -r requirements.txt")
        print("- Copy training data: cp power_log_gus.csv ml/data/power_log_raw.csv")
        return 1

if __name__ == "__main__":
    sys.exit(main())
