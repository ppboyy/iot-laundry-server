#!/usr/bin/env python3
"""
STEP 5: Train 1D CNN Classifier
- Create sequential windows
- Train 1D CNN model  
- Evaluate performance
- Export TFLite model for Raspberry Pi
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

# Configuration
WINDOW_SIZE = 15  # Use last 15 samples (7.5 minutes) for more context
TEST_SIZE = 0.2
RANDOM_STATE = 42
EPOCHS = 100
BATCH_SIZE = 32

def load_prepared_data(data_path):
    """Load prepared data from STEP 1-3"""
    print(f"📂 Loading prepared data from {data_path}")
    
    df = pd.read_csv(data_path)
    
    print(f"✅ Loaded {len(df)} samples")
    print(f"   Features: {len([col for col in df.columns if col not in ['timestamp', 'time_seconds', 'phase']])}")
    print(f"   Phases: {df['phase'].nunique()} classes")
    
    return df

def create_sequential_windows(df, window_size=WINDOW_SIZE):
    """Create sequential windows for CNN training"""
    print(f"\n🪟 Creating sequential windows (size={window_size})...")
    
    # Feature columns
    feature_cols = [col for col in df.columns 
                    if col not in ['timestamp', 'time_seconds', 'phase', 'power']]
    
    X_sequences = []
    y_labels = []
    
    # Create sliding windows - keep sequences separate (not flattened)
    for i in range(window_size, len(df)):
        # Extract window as 2D array [time_steps, features]
        window = df[feature_cols].iloc[i-window_size:i].values
        X_sequences.append(window)
        
        # Label is the current phase
        y_labels.append(df['phase'].iloc[i])
    
    X = np.array(X_sequences)
    y = np.array(y_labels)
    
    print(f"✅ Created {len(X)} sequential windows")
    print(f"   Shape: {X.shape} [samples, time_steps, features]")
    print(f"   Class distribution:")
    unique, counts = np.unique(y, return_counts=True)
    for label, count in zip(unique, counts):
        print(f"      {label:12s}: {count:4d} ({count/len(y)*100:.1f}%)")
    
    return X, y, feature_cols

def encode_labels(y_train, y_test):
    """Encode string labels to integers"""
    print(f"\n🏷️  Encoding labels...")
    
    label_encoder = LabelEncoder()
    y_train_encoded = label_encoder.fit_transform(y_train)
    y_test_encoded = label_encoder.transform(y_test)
    
    print(f"✅ Label mapping:")
    for idx, label in enumerate(label_encoder.classes_):
        print(f"   {idx}: {label}")
    
    return y_train_encoded, y_test_encoded, label_encoder

def build_cnn_model(input_shape, n_classes):
    """Build 1D CNN architecture"""
    print(f"\n🏗️  Building 1D CNN model...")
    print(f"   Input shape: {input_shape}")
    print(f"   Output classes: {n_classes}")
    
    model = models.Sequential([
        # First convolutional block - learn local patterns
        layers.Conv1D(32, kernel_size=3, activation='relu', input_shape=input_shape),
        layers.BatchNormalization(),
        layers.MaxPooling1D(pool_size=2),
        layers.Dropout(0.2),
        
        # Second convolutional block - learn higher-level patterns
        layers.Conv1D(64, kernel_size=3, activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling1D(pool_size=2),
        layers.Dropout(0.3),
        
        # Dense layers for classification
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.4),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.3),
        
        # Output layer
        layers.Dense(n_classes, activation='softmax')
    ])
    
    # Calculate class weights to handle imbalance
    from sklearn.utils.class_utils import compute_class_weight
    import numpy as np
    
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    print(f"\n📋 Model Architecture:")
def train_cnn(model, X_train, y_train, X_test, y_test, model_dir):
    """Train CNN model with callbacks"""
    print(f"\n🎓 Training CNN...")
    
    # Calculate class weights to handle imbalance
    from sklearn.utils.class_weight import compute_class_weight
    import numpy as np
    
    class_weights = compute_class_weight(
        class_weight='balanced',
        classes=np.unique(y_train),
        y=y_train
    )
    class_weight_dict = {i: weight for i, weight in enumerate(class_weights)}
    
    print(f"\n⚖️  Class weights (to handle imbalance):")
    for cls, weight in class_weight_dict.items():
        print(f"   Class {cls}: {weight:.2f}")
    
    # Callbacks
    checkpoint_path = os.path.join(model_dir, 'cnn_best_model.h5')
    callbacks = [
        EarlyStopping(
            monitor='val_loss',
            patience=15,
            restore_best_weights=True,
            verbose=1
        ),
        ModelCheckpoint(
            checkpoint_path,
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=7,
            min_lr=1e-6,
            verbose=1
        )
    ]
    
    # Train with class weights
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        class_weight=class_weight_dict,
        verbose=1,
       epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1
    )
    
    print(f"\n✅ Training complete!")
    
    return history

def evaluate_model(model, X_train, y_train, X_test, y_test, label_encoder):
    """Evaluate CNN performance"""
    print(f"\n📊 Evaluating model performance...")
    
    # Predictions
    train_pred = np.argmax(model.predict(X_train, verbose=0), axis=1)
    test_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    
    # Accuracy
    train_acc = accuracy_score(y_train, train_pred)
    test_acc = accuracy_score(y_test, test_pred)
    
    print(f"\n{'='*60}")
    print(f"Training Accuracy: {train_acc:.4f} ({train_acc*100:.2f}%)")
    print(f"Test Accuracy:     {test_acc:.4f} ({test_acc*100:.2f}%)")
    print(f"{'='*60}")
    
    # Classification report
    print(f"\n📋 Classification Report:")
    target_names = label_encoder.classes_
    print(classification_report(y_test, test_pred, target_names=target_names, digits=4))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, test_pred)
    print(f"\n🔢 Confusion Matrix:")
    print(f"\n{'Predicted →':>15}", end='')
    for label in target_names:
        print(f"{label:>12}", end='')
    print()
    print("Actual ↓")
    for i, label in enumerate(target_names):
        print(f"{label:>15}", end='')
        for j in range(len(target_names)):
            print(f"{cm[i,j]:>12}", end='')
        print()
    
    return {
        'train_accuracy': float(train_acc),
        'test_accuracy': float(test_acc),
        'confusion_matrix': cm.tolist(),
        'classification_report': classification_report(y_test, test_pred, target_names=target_names, output_dict=True)
    }

def save_model(model, label_encoder, feature_cols, metrics, model_dir):
    """Save CNN model in multiple formats"""
    print(f"\n💾 Saving model...")
    
    # Save Keras model
    keras_path = os.path.join(model_dir, 'cnn_phase_classifier.h5')
    model.save(keras_path)
    print(f"✅ Keras model saved: {keras_path}")
    
    # Convert to TFLite for Raspberry Pi
    print(f"\n🔄 Converting to TensorFlow Lite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    
    tflite_path = os.path.join(model_dir, 'cnn_phase_classifier.tflite')
    with open(tflite_path, 'wb') as f:
        f.write(tflite_model)
    print(f"✅ TFLite model saved: {tflite_path}")
    
    # Save label encoder
    import joblib
    encoder_path = os.path.join(model_dir, 'label_encoder.pkl')
    joblib.dump(label_encoder, encoder_path)
    print(f"✅ Label encoder saved: {encoder_path}")
    
    # Save metadata
    metadata = {
        'model_type': '1D_CNN',
        'window_size': WINDOW_SIZE,
        'feature_columns': feature_cols,
        'n_features': len(feature_cols),
        'classes': label_encoder.classes_.tolist(),
        'metrics': metrics,
        'trained_at': datetime.now().isoformat()
    }
    
    metadata_path = os.path.join(model_dir, 'cnn_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✅ Metadata saved: {metadata_path}")
    
    # Model sizes
    keras_size = os.path.getsize(keras_path) / (1024 * 1024)
    tflite_size = os.path.getsize(tflite_path) / (1024 * 1024)
    print(f"\n📦 Model sizes:")
    print(f"   Keras (.h5):   {keras_size:.2f} MB")
    print(f"   TFLite (.tflite): {tflite_size:.2f} MB (for RPi)")

def plot_training_history(history, model_dir):
    """Plot and save training curves"""
    print(f"\n📈 Generating training history plots...")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Accuracy
    ax1.plot(history.history['accuracy'], label='Train')
    ax1.plot(history.history['val_accuracy'], label='Validation')
    ax1.set_title('Model Accuracy')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Accuracy')
    ax1.legend()
    ax1.grid(True)
    
    # Loss
    ax2.plot(history.history['loss'], label='Train')
    ax2.plot(history.history['val_loss'], label='Validation')
    ax2.set_title('Model Loss')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Loss')
    ax2.legend()
    ax2.grid(True)
    
    plot_path = os.path.join(model_dir, 'training_history.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"✅ Training history saved: {plot_path}")
    plt.close()

def plot_confusion_matrix(cm, labels, model_dir):
    """Plot confusion matrix"""
    print(f"\n📈 Generating confusion matrix plot...")
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=labels, yticklabels=labels)
    plt.title('1D CNN - Confusion Matrix')
    plt.ylabel('Actual Phase')
    plt.xlabel('Predicted Phase')
    
    plot_path = os.path.join(model_dir, 'cnn_confusion_matrix.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"✅ Confusion matrix saved: {plot_path}")
    plt.close()

def main():
    """Main CNN training pipeline"""
    print("=" * 70)
    print("WASHING MACHINE ML - 1D CNN TRAINING")
    print("=" * 70)
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    data_path = os.path.join(project_root, 'data', 'power_log_prepared.csv')
    model_dir = os.path.join(project_root, 'models')
    
    if not os.path.exists(data_path):
        print(f"❌ Prepared data not found: {data_path}")
        print(f"   Please run: python training/prepare_data.py first")
        return
    
    try:
        # Load data
        df = load_prepared_data(data_path)
        
        # Create sequential windows
        X, y, feature_cols = create_sequential_windows(df, WINDOW_SIZE)
        
        # Split data
        print(f"\n✂️  Splitting data (train={1-TEST_SIZE:.0%}, test={TEST_SIZE:.0%})...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
        )
        print(f"   Train: {len(X_train)} samples")
        print(f"   Test:  {len(X_test)} samples")
        
        # Encode labels
        y_train_enc, y_test_enc, label_encoder = encode_labels(y_train, y_test)
        
        # Build model
        input_shape = (X_train.shape[1], X_train.shape[2])  # (time_steps, features)
        n_classes = len(label_encoder.classes_)
        model = build_cnn_model(input_shape, n_classes)
        
        # Train
        history = train_cnn(model, X_train, y_train_enc, X_test, y_test_enc, model_dir)
        
        # Evaluate
        metrics = evaluate_model(model, X_train, y_train_enc, X_test, y_test_enc, label_encoder)
        
        # Plot results
        plot_training_history(history, model_dir)
        cm = confusion_matrix(y_test_enc, np.argmax(model.predict(X_test, verbose=0), axis=1))
        plot_confusion_matrix(cm, label_encoder.classes_, model_dir)
        
        # Save model
        save_model(model, label_encoder, feature_cols, metrics, model_dir)
        
        print("\n" + "=" * 70)
        print("✅ 1D CNN TRAINING COMPLETE!")
        print("=" * 70)
        print(f"\nModel Performance Summary:")
        print(f"   Test Accuracy: {metrics['test_accuracy']*100:.2f}%")
        print(f"\nNext steps:")
        print(f"1. Deploy TFLite model to RPi: cnn_phase_classifier.tflite")
        print(f"2. Use with TFLite interpreter for inference")
        
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
