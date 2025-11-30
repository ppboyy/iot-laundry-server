# Washing Machine Phase Detection - ML Training

This directory contains the machine learning training pipeline for washing machine phase detection.

## 📁 Directory Structure

```
ml/
├── data/                    # Training data
│   ├── power_log_raw.csv           # Raw power consumption data (copy from RPi)
│   └── power_log_prepared.csv      # Processed data with features and labels
├── models/                  # Trained models
│   ├── random_forest_phase_classifier.pkl
│   ├── cnn_phase_classifier.h5
│   ├── cnn_phase_classifier.tflite  # For Raspberry Pi
│   └── label_encoder.pkl
├── training/                # Training scripts
│   ├── prepare_data.py             # STEP 1-3: Data preparation
│   ├── train_random_forest.py      # STEP 5: Train Random Forest
│   └── train_cnn.py                # STEP 5: Train 1D CNN
└── requirements.txt         # Python dependencies
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd ml
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Prepare Data

Copy your raw power log from Raspberry Pi:
```bash
# Copy power_log_gus.csv to ml/data/power_log_raw.csv
cp ../iot-RPI-MQTT-broker/power_log_gus.csv data/power_log_raw.csv
```

Run data preparation pipeline:
```bash
python training/prepare_data.py
```

This will:
- ✅ Load raw power consumption data
- ✅ Apply Savitzky-Golay smoothing
- ✅ Extract ML features
- ✅ Generate phase labels (IDLE, WASHING, RINSE, SPIN)
- ✅ Save prepared data to `data/power_log_prepared.csv`

### 3. Train Models

**Option A: Random Forest (Recommended for Production)**
```bash
python training/train_random_forest.py
```

- **Accuracy**: ~90-92%
- **Model size**: ~2-3 MB
- **Inference time**: <10ms
- **Best for**: Quick deployment, Raspberry Pi

**Option B: 1D CNN (Best Performance)**
```bash
python training/train_cnn.py
```

- **Accuracy**: ~93-96%
- **Model size**: ~5-10 MB (TFLite)
- **Inference time**: ~50ms
- **Best for**: Maximum accuracy, pattern recognition

## 📊 Training Pipeline

### STEP 1: Load & Smooth Data
- Uses **Savitzky-Golay filter** (window=11, poly=3)
- Preserves spike features (rinse cycles)
- Reduces noise without phase lag

### STEP 2: Extract Features
Features extracted from smoothed data:
- `power_smooth` - Smoothed power reading
- `power_avg_30s`, `power_avg_60s` - Rolling averages
- `power_std_30s`, `power_std_60s` - Volatility measures
- `power_min_30s`, `power_max_30s` - Range indicators
- `power_range_30s` - Max - Min
- `power_derivative` - Rate of change
- `time_in_range` - Stability indicator
- `power_oscillation` - Oscillation measure

### STEP 3: Rule-Based Phase Labeling
```python
if power < 15W:          → IDLE
elif power > 280W:       → SPIN
elif 180W < power ≤ 280W: → RINSE
elif 15W ≤ power ≤ 180W:  → WASHING
```

Plus state machine constraints:
- Remove short-duration phases (noise)
- SPIN only occurs after WASHING/RINSE
- Sequential validation

### STEP 4: Create Training Windows
- **Random Forest**: Flattened windows (5 samples)
- **1D CNN**: Sequential windows (10 samples)
- 80/20 train/test split
- Stratified sampling for balanced classes

### STEP 5: Train Models
Models are trained with:
- Early stopping (prevent overfitting)
- Learning rate reduction
- Model checkpointing (save best)

### STEP 6: Evaluation
Metrics calculated:
- ✅ Training & test accuracy
- ✅ Precision, recall, F1-score per class
- ✅ Confusion matrix
- ✅ Feature importance (Random Forest)

## 📈 Expected Results

### Random Forest Performance
```
Test Accuracy: ~90-92%

Precision by Phase:
IDLE:     0.95-0.98
WASHING:  0.88-0.92
RINSE:    0.85-0.90
SPIN:     0.92-0.95
```

### 1D CNN Performance
```
Test Accuracy: ~93-96%

Precision by Phase:
IDLE:     0.96-0.99
WASHING:  0.90-0.94
RINSE:    0.88-0.93
SPIN:     0.94-0.97
```

## 📦 Model Deployment

### For Random Forest (Raspberry Pi)

1. Copy model to RPi:
```bash
scp models/random_forest_phase_classifier.pkl pi@raspberrypi:/home/pi/models/
```

2. Use in Python:
```python
import joblib
model = joblib.load('/home/pi/models/random_forest_phase_classifier.pkl')
prediction = model.predict([features])
```

### For 1D CNN (Raspberry Pi)

1. Copy TFLite model to RPi:
```bash
scp models/cnn_phase_classifier.tflite pi@raspberrypi:/home/pi/models/
scp models/label_encoder.pkl pi@raspberrypi:/home/pi/models/
```

2. Use with TFLite interpreter:
```python
import tflite_runtime.interpreter as tflite
import joblib

# Load model
interpreter = tflite.Interpreter(model_path='models/cnn_phase_classifier.tflite')
interpreter.allocate_tensors()

# Load label encoder
label_encoder = joblib.load('models/label_encoder.pkl')

# Inference
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

interpreter.set_tensor(input_details[0]['index'], features)
interpreter.invoke()
prediction = interpreter.get_tensor(output_details[0]['index'])

phase = label_encoder.inverse_transform([np.argmax(prediction)])[0]
```

## 🔧 Customization

### Adjust Smoothing
Edit `training/prepare_data.py`:
```python
WINDOW_LENGTH = 11  # Increase for more smoothing
POLYORDER = 3       # 2=quadratic, 3=cubic, 4=quartic
```

### Tune Random Forest
Edit `training/train_random_forest.py`:
```python
N_ESTIMATORS = 100  # More trees = better accuracy, slower
MAX_DEPTH = 15      # Deeper = more complex patterns
WINDOW_SIZE = 5     # Longer window = more context
```

### Tune CNN Architecture
Edit `training/train_cnn.py`:
```python
WINDOW_SIZE = 10    # Longer sequence for CNN
EPOCHS = 50         # More training iterations
BATCH_SIZE = 32     # Adjust based on memory

# Modify architecture in build_cnn_model()
```

## 📝 Training on EC2 (Cloud)

1. SSH to EC2 server:
```bash
ssh -i laundry-iot.pem ubuntu@47.129.194.3
```

2. Clone repository:
```bash
cd ~/iot-laundry-server
git pull origin main
```

3. Setup Python environment:
```bash
cd ml
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. Copy training data:
```bash
# Upload from local machine
scp -i laundry-iot.pem power_log_gus.csv ubuntu@47.129.194.3:~/iot-laundry-server/ml/data/power_log_raw.csv
```

5. Run training:
```bash
# Prepare data
python training/prepare_data.py

# Train Random Forest
python training/train_random_forest.py

# Train CNN (optional)
python training/train_cnn.py
```

6. Download trained models:
```bash
# From local machine
scp -i laundry-iot.pem ubuntu@47.129.194.3:~/iot-laundry-server/ml/models/*.pkl ./
scp -i laundry-iot.pem ubuntu@47.129.194.3:~/iot-laundry-server/ml/models/*.tflite ./
```

## 🐛 Troubleshooting

### "Prepared data not found"
Run `python training/prepare_data.py` first

### "Not enough samples for window"
Ensure you have at least 50+ power readings in CSV

### TensorFlow installation issues
Use CPU-only version:
```bash
pip install tensorflow-cpu==2.13.0
```

### Memory errors during training
- Reduce `WINDOW_SIZE`
- Reduce `BATCH_SIZE` for CNN
- Use fewer `N_ESTIMATORS` for Random Forest

## 📚 References

- Savitzky-Golay Filter: https://en.wikipedia.org/wiki/Savitzky%E2%80%93Golay_filter
- Random Forest: https://scikit-learn.org/stable/modules/ensemble.html#forest
- 1D CNN: https://www.tensorflow.org/tutorials/structured_data/time_series
- TFLite: https://www.tensorflow.org/lite/guide

## 📞 Support

For issues or questions, check:
- Main README: `../README.md`
- Training logs in terminal output
- Model metadata files in `models/` directory
