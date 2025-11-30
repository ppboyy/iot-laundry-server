# Quick Start Guide - ML Training

## ⚡ Train Models in 3 Steps

### Step 1: Setup (One-time)

**Windows:**
```powershell
cd ml
.\setup.bat
```

**Linux/Mac/EC2:**
```bash
cd ml
chmod +x setup.sh
./setup.sh
```

### Step 2: Prepare Data

```bash
# Activate environment first
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Run data preparation
python training/prepare_data.py
```

**Expected output:**
```
📂 Loading data from power_log_raw.csv
✅ Loaded 2459 samples
   Duration: 46.3 minutes
   Power range: 5.9W - 380.2W

🔧 Applying Savitzky-Golay filter (window=11, poly=3)
✅ Smoothing complete
   Noise reduction: 45.3%

🔍 Extracting features...
✅ Extracted features

🏷️  Generating rule-based phase labels...
✅ Phase label distribution:
   IDLE        :  280 samples (11.4%) ~4.7 min
   WASHING     : 1450 samples (59.0%) ~24.2 min
   RINSE       :  380 samples (15.5%) ~6.3 min
   SPIN        :  349 samples (14.2%) ~5.8 min

💾 Saving prepared data
✅ DATA PREPARATION COMPLETE!
```

### Step 3: Train Model

**Random Forest (Recommended):**
```bash
python training/train_random_forest.py
```

**Expected time:** ~2-5 minutes

**Expected output:**
```
Training Accuracy: 0.9534 (95.34%)
Test Accuracy:     0.9187 (91.87%)

Top 10 Most Important Features:
   power_smooth        : 0.2345
   power_avg_60s       : 0.1823
   power_derivative    : 0.1234
   ...

✅ RANDOM FOREST TRAINING COMPLETE!
Model: ml/models/random_forest_phase_classifier.pkl
```

**1D CNN (Best Performance):**
```bash
python training/train_cnn.py
```

**Expected time:** ~15-30 minutes (depends on CPU/GPU)

## 📊 What Gets Created

After training, you'll have:

```
ml/
├── data/
│   ├── power_log_raw.csv              ← Input data
│   └── power_log_prepared.csv         ← Processed with features
├── models/
│   ├── random_forest_phase_classifier.pkl  ← Deploy this to RPi
│   ├── random_forest_metadata.json
│   ├── confusion_matrix.png
│   ├── cnn_phase_classifier.tflite    ← Or deploy this (better)
│   ├── cnn_metadata.json
│   └── label_encoder.pkl
```

## 🚀 Deploy to Raspberry Pi

### Method 1: SCP from local machine
```bash
# Copy Random Forest model
scp ml/models/random_forest_phase_classifier.pkl pi@192.168.1.100:/home/pi/models/

# Or copy CNN model
scp ml/models/cnn_phase_classifier.tflite pi@192.168.1.100:/home/pi/models/
scp ml/models/label_encoder.pkl pi@192.168.1.100:/home/pi/models/
```

### Method 2: Direct from EC2
```bash
# On Raspberry Pi
scp ubuntu@47.129.194.3:~/iot-laundry-server/ml/models/random_forest_phase_classifier.pkl /home/pi/models/
```

## 🔍 Verify Training

### Check model accuracy
Look for:
- ✅ Test Accuracy > 90%
- ✅ All phases have precision > 0.85
- ✅ No phase has recall < 0.80

### Review confusion matrix
Open: `ml/models/confusion_matrix.png`

Good signs:
- Dark diagonal (correct predictions)
- Light off-diagonal (few mistakes)
- RINSE might confuse with WASHING (acceptable)

### Test inference speed
```bash
python -c "
import joblib
import time
import numpy as np

model = joblib.load('models/random_forest_phase_classifier.pkl')
X = np.random.rand(1, 60)  # 60 features (12 features × 5 window)

start = time.time()
for _ in range(100):
    model.predict(X)
elapsed = (time.time() - start) / 100

print(f'Average inference time: {elapsed*1000:.2f}ms')
"
```

Should be < 10ms for Random Forest, < 50ms for CNN.

## 🐛 Common Issues

### "No module named 'sklearn'"
```bash
pip install scikit-learn
```

### "No module named 'tensorflow'"
```bash
pip install tensorflow  # Or tensorflow-cpu for no GPU
```

### "power_log_raw.csv not found"
```bash
# Copy your data file
cp ../iot-RPI-MQTT-broker/power_log_gus.csv ml/data/power_log_raw.csv
```

### Low accuracy (< 85%)
- Check if you have complete cycle data (idle → wash → rinse → spin → idle)
- Try increasing WINDOW_SIZE in training scripts
- Collect more training data from different machines

### Out of memory during CNN training
Edit `training/train_cnn.py`:
```python
BATCH_SIZE = 16  # Reduce from 32
WINDOW_SIZE = 5  # Reduce from 10
```

## 📈 Improve Model Performance

### Collect more data
```python
# Combine multiple washing cycles
import pandas as pd

df1 = pd.read_csv('cycle1.csv')
df2 = pd.read_csv('cycle2.csv')
df3 = pd.read_csv('cycle3.csv')

combined = pd.concat([df1, df2, df3], ignore_index=True)
combined.to_csv('ml/data/power_log_raw.csv', index=False)
```

### Tune hyperparameters
Random Forest:
```python
N_ESTIMATORS = 200  # More trees
MAX_DEPTH = 20      # Deeper trees
WINDOW_SIZE = 7     # Longer context
```

CNN:
```python
WINDOW_SIZE = 15    # Longer sequences
EPOCHS = 100        # More training
# Add more Conv1D layers
```

### Use data augmentation
In `prepare_data.py`, add noise variations:
```python
# Add ±5% power variation
df_aug = df.copy()
df_aug['power'] *= np.random.uniform(0.95, 1.05, len(df))
```

## ✅ Success Checklist

- [ ] Setup completed without errors
- [ ] Data preparation shows 4 phases (IDLE, WASHING, RINSE, SPIN)
- [ ] Training completes with > 90% test accuracy
- [ ] Model file exists in `ml/models/`
- [ ] Confusion matrix shows strong diagonal
- [ ] Inference time < 10ms (RF) or < 50ms (CNN)
- [ ] Model copied to Raspberry Pi successfully

## 🎯 Next Steps

After successful training:

1. **Integrate into washing_machine_monitor_v2.py**
   - See `../iot-RPI-MQTT-broker/README.md`
   - Use MLPhaseDetector class

2. **Test with live data**
   - Run simulator or real washing machine
   - Monitor phase detection accuracy

3. **Deploy to production**
   - Setup systemd service on RPi
   - Monitor logs for issues

4. **Retrain periodically**
   - Collect new data monthly
   - Retrain to adapt to machine wear

---

**Need help?** Check the full README: `ml/README.md`
