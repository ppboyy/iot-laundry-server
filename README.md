# IoT Laundry Server

Backend server for IoT laundry monitoring system. Receives real-time data from AWS IoT Core and provides REST API for frontend dashboard.

## System Architecture

```
ESP32 (Hall Sensor) ──┐
                      ├──> Local MQTT Broker (RPi) ──> washing_machine_monitor_v3.py
Shelly Plug (Power) ──┘                                            │
                                                                    ├──> ML Phase Detector (Random Forest)
                                                                    │
                                                                    └──> AWS IoT Core ──> EC2 Backend ──> PostgreSQL RDS
                                                                                               │
                                                                                               └──> REST API ──> Vercel Frontend

ML Training Pipeline (iot-laundry-server/ml) trains phase detection models → Deployed to RPi
```


## Components

1. **server.js**: Express REST API server (port 3000)
2. **iot-subscriber.js**: AWS IoT Core MQTT subscriber (receives data from RPi)
3. **routes/api.js**: REST API endpoint definitions
4. **config/database.js**: PostgreSQL connection and table initialization
5. **ml/**: Machine learning training pipeline (Random Forest & CNN models)

## Prerequisites

- Node.js (v14 or higher)
- AWS RDS PostgreSQL database
- AWS IoT Core certificates (for iot-subscriber.js)
- EC2 instance (recommended) or local server

## Installation

1. **Clone repository:**
   ```bash
   git clone https://github.com/yourusername/iot-laundry-server.git
   cd iot-laundry-server
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment variables:**
   
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your credentials:
   ```env
   # Server Configuration
   PORT=3000
   NODE_ENV=production
   
   # PostgreSQL Database
   DB_TYPE=postgres
   DB_HOST=<INSERT DB INSTANCE>
   DB_PORT=5432
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_NAME=laundry_iot
   
   # AWS IoT Core (for iot-subscriber.js)
   IOT_ENDPOINT=<INSERT IOT ENDPOINT>
   IOT_CLIENT_ID=backend-subscriber
   IOT_CA_PATH=./certs/AmazonRootCA1.pem
   IOT_CERT_PATH=./certs/device.pem.crt
   IOT_KEY_PATH=./certs/private.pem.key
   
   # CORS - Add your Vercel frontend URL
   ALLOWED_ORIGINS=https://www.iotwasher.com,http://localhost:3000
   ```

4. **Add AWS IoT Core certificates:**
   ```bash
   mkdir certs
   # Copy your AWS IoT certificates to certs/ folder
   # - AmazonRootCA1.pem
   # - device.pem.crt
   # - private.pem.key
   ```

## Database Setup

Tables are **automatically created** when `iot-subscriber.js` starts for the first time.

### Table Structure

**machine_live_status** - Current state of 4 machines
```sql
CREATE TABLE machine_live_status (
  machine_id VARCHAR(10) PRIMARY KEY,  -- WM-01, WM-02, WM-03, WM-04
  data JSONB NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**machine_readings_log** - Historical data (append-only)
```sql
CREATE TABLE machine_readings_log (
  id SERIAL PRIMARY KEY,
  data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Data Format (v3 with ML)
```json
{
  "timestamp": "2025-12-02T12:00:00.000Z",
  "MachineID": "WM-01",
  "cycle_number": 5,
  "current": 250.5,
  "state": "RUNNING",
  "door_opened": false,
  "ml_phase": "WASHING",
  "ml_confidence": 0.87
}
```

**Rule-Based States**: `IDLE` (door open), `RUNNING` (washing), `OCCUPIED` (finished)

**ML Phases**: `WASHING` (200-220W), `RINSE` (100-150W), `SPIN` (300-700W), `IDLE` (<10W)

## Running the Server

### Option 1: Direct Node.js (for testing)
```bash
# Terminal 1 - API Server
node server.js

# Terminal 2 - IoT Subscriber
node iot-subscriber.js
```

### Option 2: With PM2 (recommended for production)
```bash
# Start both services
pm2 start server.js --name washer-backend
pm2 start iot-subscriber.js --name iot-subscriber

# View logs
pm2 logs

# Save process list (auto-restart on reboot)
pm2 save
pm2 startup

# Manage processes
pm2 list
pm2 restart washer-backend
pm2 stop iot-subscriber
```

### Option 3: Background with nohup
```bash
nohup node server.js > server.log 2>&1 &
nohup node iot-subscriber.js > subscriber.log 2>&1 &
```

## API Endpoints

### Live Machine Status (Dashboard)
- `GET /api/live` - Get current status of all 4 machines
- `GET /api/live/:machineId` - Get current status of specific machine (e.g., `/api/live/WM-01`)

### Historical Data (Analytics)
- `GET /api/readings?limit=100` - Get recent log entries
- `GET /api/readings/:id` - Get specific log entry by ID
- `GET /api/machines/:machineId/readings?limit=100` - Get history for specific machine

### Dashboard & Summary
- `GET /api/dashboard` - Statistics (total machines, running, idle, occupied)
- `GET /api/machines` - List all machines with current data

### Diagnostics
- `GET /health` - Server health check
- `GET /api/diagnostics` - Database tables and record counts


## 🤖 Machine Learning Phase Detection

Complete ML training pipeline for washing machine phase detection. Train models on this server, then deploy to Raspberry Pi for real-time inference.

### Quick Start

```bash
cd ml

# Windows
setup.bat

# Linux/Mac
./setup.sh

# Prepare training data (STEP 1-3)
python training/prepare_data.py

# Train Random Forest model (STEP 5)
python training/train_random_forest.py

# Deploy to Raspberry Pi
scp models/random_forest_phase_classifier.pkl andrea@rpi:/home/andrea/iot-broker/
```
