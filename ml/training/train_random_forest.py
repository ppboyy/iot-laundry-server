#!/usr/bin/env python3
"""
STEP 5: Train Random Forest Classifier
- Create training windows
- Train Random Forest model
- Evaluate performance
- Save model for deployment
"""

import pandas as pd
import numpy as np
import os
import json
import joblib
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
WINDOW_SIZE = 15  # Use last 15 samples (7.5 minutes) for prediction - more context
TEST_SIZE = 0.2
RANDOM_STATE = 42
N_ESTIMATORS = 200  # More trees for better accuracy
MAX_DEPTH = 20  # Deeper trees to capture complex patterns

def load_prepared_data(data_path):
    """Load prepared data from STEP 1-3"""
    print(f"📂 Loading prepared data from {data_path}")
    
    df = pd.read_csv(data_path)
    
    print(f"✅ Loaded {len(df)} samples")
    print(f"   Features: {len([col for col in df.columns if col not in ['timestamp', 'time_seconds', 'phase']])}")
    print(f"   Phases: {df['phase'].nunique()} classes")
    
    return df

def create_training_windows(df, window_size=WINDOW_SIZE):
    """Create sliding window sequences for training"""
    print(f"\n🪟 Creating training windows (size={window_size})...")
    
    # Feature columns (exclude metadata and label)
    feature_cols = [col for col in df.columns 
                    if col not in ['timestamp', 'time_seconds', 'phase', 'power']]
    
    X_windows = []
    y_labels = []
    
    # Create sliding windows
    for i in range(window_size, len(df)):
        # Extract window of features
        window = df[feature_cols].iloc[i-window_size:i].values
        
        # Flatten window into single feature vector
        X_windows.append(window.flatten())
        
        # Label is the current phase (what we want to predict)
        y_labels.append(df['phase'].iloc[i])
    
    X = np.array(X_windows)
    y = np.array(y_labels)
    
    print(f"✅ Created {len(X)} training windows")
    print(f"   Feature vector size: {X.shape[1]}")
    print(f"   Class distribution:")
    unique, counts = np.unique(y, return_counts=True)
    for label, count in zip(unique, counts):
        print(f"      {label:12s}: {count:4d} ({count/len(y)*100:.1f}%)")
    
    return X, y, feature_cols

def train_random_forest(X_train, y_train, sample_weights=None):
    """Train Random Forest classifier"""
    print(f"\n🌳 Training Random Forest...")
    print(f"   n_estimators: {N_ESTIMATORS}")
    print(f"   max_depth: {MAX_DEPTH}")
    print(f"   Training samples: {len(X_train)}")
    
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,  # Use all CPU cores
        verbose=1,
        class_weight='balanced'  # Handle class imbalance
    )
    
    model.fit(X_train, y_train, sample_weight=sample_weights)
    
    print(f"✅ Training complete!")
    
    return model

def evaluate_model(model, X_train, y_train, X_test, y_test):
    """Evaluate model performance"""
    print(f"\n📊 Evaluating model performance...")
    
    # Training accuracy
    train_pred = model.predict(X_train)
    train_acc = accuracy_score(y_train, train_pred)
    
    # Test accuracy
    test_pred = model.predict(X_test)
    test_acc = accuracy_score(y_test, test_pred)
    
    print(f"\n{'='*60}")
    print(f"Training Accuracy: {train_acc:.4f} ({train_acc*100:.2f}%)")
    print(f"Test Accuracy:     {test_acc:.4f} ({test_acc*100:.2f}%)")
    print(f"{'='*60}")
    
    # Classification report
    print(f"\n📋 Classification Report:")
    print(classification_report(y_test, test_pred, digits=4))
    
    # Confusion matrix
    print(f"\n🔢 Confusion Matrix:")
    cm = confusion_matrix(y_test, test_pred)
    labels = sorted(np.unique(y_test))
    
    # Print confusion matrix
    print(f"\n{'Predicted →':>15}", end='')
    for label in labels:
        print(f"{label:>12}", end='')
    print()
    print("Actual ↓")
    for i, label in enumerate(labels):
        print(f"{label:>15}", end='')
        for j in range(len(labels)):
            print(f"{cm[i,j]:>12}", end='')
        print()
    
    # Feature importance
    print(f"\n🎯 Top 10 Most Important Features:")
    feature_names = [f"feat_{i}" for i in range(X_train.shape[1])]
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importance.head(10).iterrows():
        print(f"   {row['feature']:20s}: {row['importance']:.4f}")
    
    return {
        'train_accuracy': train_acc,
        'test_accuracy': test_acc,
        'confusion_matrix': cm.tolist(),
        'classification_report': classification_report(y_test, test_pred, output_dict=True),
        'feature_importance': feature_importance.to_dict('records')
    }

def save_model(model, feature_cols, metrics, output_dir):
    """Save trained model and metadata"""
    print(f"\n💾 Saving model...")
    
    # Save model
    model_path = os.path.join(output_dir, 'random_forest_phase_classifier.pkl')
    joblib.dump(model, model_path)
    print(f"✅ Model saved to: {model_path}")
    
    # Save metadata
    metadata = {
        'model_type': 'RandomForestClassifier',
        'window_size': WINDOW_SIZE,
        'n_estimators': N_ESTIMATORS,
        'max_depth': MAX_DEPTH,
        'feature_columns': feature_cols,
        'n_features': len(feature_cols) * WINDOW_SIZE,
        'metrics': metrics,
        'trained_at': datetime.now().isoformat()
    }
    
    metadata_path = os.path.join(output_dir, 'random_forest_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✅ Metadata saved to: {metadata_path}")
    
    # Calculate model size
    model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"   Model size: {model_size_mb:.2f} MB")
    
    return model_path, metadata_path

def plot_confusion_matrix(cm, labels, output_dir):
    """Plot and save confusion matrix visualization"""
    print(f"\n📈 Generating confusion matrix plot...")
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=labels, yticklabels=labels)
    plt.title('Random Forest - Confusion Matrix')
    plt.ylabel('Actual Phase')
    plt.xlabel('Predicted Phase')
    
    plot_path = os.path.join(output_dir, 'confusion_matrix.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"✅ Confusion matrix saved to: {plot_path}")
    plt.close()

def main():
    """Main training pipeline"""
    print("=" * 70)
    print("WASHING MACHINE ML - RANDOM FOREST TRAINING")
    print("=" * 70)
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    data_path = os.path.join(project_root, 'data', 'power_log_prepared.csv')
    model_dir = os.path.join(project_root, 'models')
    
    # Check if prepared data exists
    if not os.path.exists(data_path):
        print(f"❌ Prepared data not found: {data_path}")
        print(f"   Please run: python training/prepare_data.py first")
        return
    
    try:
        # Load prepared data
        df = load_prepared_data(data_path)
        
        # Create training windows
        X, y, feature_cols = create_training_windows(df, WINDOW_SIZE)
        
        # Split train/test
        print(f"\n✂️  Splitting data (train={1-TEST_SIZE:.0%}, test={TEST_SIZE:.0%})...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
        )
        print(f"   Train: {len(X_train)} samples")
        print(f"   Test:  {len(X_test)} samples")
        
        # Calculate class weights to handle imbalance
        from sklearn.utils.class_weight import compute_sample_weight
        sample_weights = compute_sample_weight('balanced', y_train)
        print(f"\n⚖️  Applied balanced class weights for imbalanced dataset")
        
        # Train model
        model = train_random_forest(X_train, y_train, sample_weights)
        
        # Evaluate
        metrics = evaluate_model(model, X_train, y_train, X_test, y_test)
        
        # Plot confusion matrix
        cm = confusion_matrix(y_test, model.predict(X_test))
        labels = sorted(np.unique(y_test))
        plot_confusion_matrix(cm, labels, model_dir)
        
        # Save model
        save_model(model, feature_cols, metrics, model_dir)
        
        print("\n" + "=" * 70)
        print("✅ RANDOM FOREST TRAINING COMPLETE!")
        print("=" * 70)
        print(f"\nModel Performance Summary:")
        print(f"   Test Accuracy: {metrics['test_accuracy']*100:.2f}%")
        print(f"\nNext steps:")
        print(f"1. Review model: {os.path.join(model_dir, 'random_forest_phase_classifier.pkl')}")
        print(f"2. Deploy to RPi: Copy model file to Raspberry Pi")
        print(f"3. Integrate: Use MLPhaseDetector class in washing_machine_monitor_v2.py")
        
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
