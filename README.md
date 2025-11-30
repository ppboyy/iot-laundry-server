# IoT Laundry Server

Backend server for IoT laundry monitoring system. Receives real-time data from AWS IoT Core and provides REST API for frontend dashboard.

## System Architecture

```
ESP32 (Hall Sensor) ──┐
                      ├──> Local MQTT Broker (Raspberry Pi) ──> AWS IoT Core ──> EC2 Backend ──> PostgreSQL RDS
Shelly Plug (Power) ──┘                                                              │
                                                                                      ├──> REST API ──> Vercel Frontend
                                                                                      │
                                                            Raspberry Pi Monitor Script publishes aggregated data every 30s
                                                                                      
                                                            ML Training (EC2/Cloud) trains phase detection models
```

## Features

- **Dual-table Architecture**: Separate tables for historical logs and live machine status
- **AWS IoT Core Integration**: Real-time MQTT data ingestion from Raspberry Pi
- **REST API**: Express.js endpoints for frontend dashboard
- **PostgreSQL RDS**: Optimized for AWS with JSONB support
- **Live Status Table**: Always contains current state of 4 machines (WM-01 to WM-04)
- **Historical Log Table**: Append-only log of all data submissions
- **CORS Configured**: Ready for Vercel frontend integration
- **🆕 ML Training Pipeline**: Cloud-based training for washing machine phase detection (Random Forest & 1D CNN)

## Components

1. **server.js**: Express REST API server (port 3000)
2. **iot-subscriber.js**: AWS IoT Core MQTT subscriber
3. **routes/api.js**: API endpoint definitions
4. **config/database.js**: PostgreSQL connection and table initialization

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
   DB_HOST=iot-laundry-database.chi20c6aago7.ap-southeast-1.rds.amazonaws.com
   DB_PORT=5432
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_NAME=laundry_iot
   
   # AWS IoT Core (for iot-subscriber.js)
   IOT_ENDPOINT=a5916n61elm51-ats.iot.ap-southeast-1.amazonaws.com
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

### Data Format
```json
{
  "timestamp": "2025-11-30T12:00:00.000Z",
  "MachineID": "WM-01",
  "cycle_number": 5,
  "current": 250.5,
  "state": "RUNNING",
  "door_opened": false
}
```

**States**: `IDLE`, `RUNNING`, `OCCUPIED`

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

### Example Responses

**GET /api/live/WM-01**
```json
{
  "success": true,
  "data": {
    "machine_id": "WM-01",
    "data": {
      "timestamp": "2025-11-30T12:00:00.000Z",
      "MachineID": "WM-01",
      "cycle_number": 5,
      "current": 250.5,
      "state": "RUNNING",
      "door_opened": false
    },
    "updated_at": "2025-11-30T12:00:15.000Z"
  }
}
```

**GET /api/dashboard**
```json
{
  "success": true,
  "data": {
    "total_machines": 4,
    "running_machines": 2,
    "idle_machines": 1,
    "occupied_machines": 1,
    "avg_current": 125.3
  }
}
```

## Connecting to Vercel Frontend

In your Vercel frontend (`https://www.iotwasher.com`), fetch data using:

```javascript
// React/Next.js example - Fetch live machine status
const API_BASE = 'http://47.129.194.3:3000/api';

const fetchLiveMachines = async () => {
  try {
    const response = await fetch(`${API_BASE}/live`);
    const result = await response.json();
    
    if (result.success) {
      // result.data contains array of 4 machines
      console.log(result.data);
    }
  } catch (error) {
    console.error('Error fetching machines:', error);
  }
};

// Fetch specific machine
const fetchMachine = async (machineId) => {
  const response = await fetch(`${API_BASE}/live/${machineId}`);
  const result = await response.json();
  return result.data;
};

// Fetch dashboard stats
const fetchDashboard = async () => {
  const response = await fetch(`${API_BASE}/dashboard`);
  return await response.json();
};
```

## Deployment (AWS EC2)

Current deployment: `http://47.129.194.3:3000`

### Initial Setup
```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@47.129.194.3

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install PM2 globally
sudo npm install -g pm2

# Clone repository
git clone https://github.com/yourusername/iot-laundry-server.git
cd iot-laundry-server

# Install dependencies
npm install

# Configure .env file
nano .env
# (Add your database and AWS IoT credentials)

# Create certs directory and add certificates
mkdir certs
# Upload your AWS IoT certificates to certs/

# Start services with PM2
pm2 start server.js --name washer-backend
pm2 start iot-subscriber.js --name iot-subscriber

# Save PM2 configuration
pm2 save
pm2 startup

# Check status
pm2 list
pm2 logs
```

### Updating Code
```bash
cd ~/iot-laundry-server
git pull origin main
npm install
pm2 restart washer-backend
pm2 restart iot-subscriber
pm2 logs
```

## Data Flow

1. **ESP32** publishes hall sensor data → Local MQTT broker on Raspberry Pi
2. **Shelly Plug** publishes power data → Local MQTT broker on Raspberry Pi
3. **Raspberry Pi** (`washing_machine_monitor_v2.py`) aggregates data every 30 seconds → AWS IoT Core
4. **iot-subscriber.js** receives from AWS IoT Core → Writes to PostgreSQL:
   - Inserts into `machine_readings_log` (historical)
   - Upserts into `machine_live_status` (current state)
5. **Vercel Frontend** fetches from REST API → Displays dashboard

## Security Considerations

- ✅ Certificates stored in `certs/` directory (excluded from git via `.gitignore`)
- ✅ Never commit `.env` file to version control
- ✅ CORS configured to allow only Vercel domain
- ✅ AWS RDS security group restricts database access to EC2 only
- ✅ PostgreSQL uses SSL/TLS connection (`rejectUnauthorized: false` for AWS RDS)
- ✅ AWS IoT Core uses certificate-based authentication

## Troubleshooting

**API Endpoints Not Working:**
- Check if server is running: `pm2 list`
- View logs: `pm2 logs washer-backend`
- Restart server: `pm2 restart washer-backend`
- Verify port 3000 is not in use: `sudo lsof -i :3000`

**No Data in Database:**
- Check IoT subscriber: `pm2 logs iot-subscriber`
- Verify Raspberry Pi is publishing to AWS IoT Core
- Test database connection: `GET /api/diagnostics`

**Database Connection Failed:**
- Verify RDS security group allows inbound from EC2
- Check database credentials in `.env`
- Test with: `psql -h your-endpoint -U postgres -d laundry_iot`

**CORS Errors:**
- Add your Vercel domain to `ALLOWED_ORIGINS` in `.env`
- Restart server after changing environment variables

## Files Structure

```
iot-laundry-server/
├── server.js                 # Main Express API server
├── iot-subscriber.js         # AWS IoT Core MQTT subscriber
├── package.json              # Dependencies
├── .env                      # Environment variables (not in git)
├── .env.example              # Environment template
├── .gitignore                # Excludes certs/, .env
├── README.md                 # This file
├── config/
│   └── database.js           # PostgreSQL connection & table creation
├── routes/
│   └── api.js                # REST API endpoints
├── certs/                    # AWS IoT certificates (not in git)
│   ├── AmazonRootCA1.pem
│   ├── device.pem.crt
│   └── private.pem.key
├── ml/                       # 🆕 Machine Learning Training Pipeline
│   ├── data/                 # Training datasets
│   ├── models/               # Trained models (Random Forest, CNN)
│   ├── training/             # Training scripts
│   ├── README.md             # Detailed ML documentation
│   ├── QUICKSTART.md         # Quick training guide
│   └── requirements.txt      # Python dependencies
└── IOT_SUBSCRIBER_SETUP.md   # Detailed setup guide for EC2
```

## 🤖 Machine Learning Phase Detection

This repository now includes a complete ML training pipeline for washing machine phase detection.

### Quick Start

```bash
cd ml
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Prepare training data
python training/prepare_data.py

# Train model (choose one)
python training/train_random_forest.py  # Fast, 90-92% accuracy
python training/train_cnn.py            # Best, 93-96% accuracy
```

### Features
- **Savitzky-Golay filtering** for optimal smoothing
- **Random Forest** classifier (~90-92% accuracy, <10ms inference)
- **1D CNN** classifier (~93-96% accuracy, ~50ms inference)
- **Automatic feature extraction** from power consumption patterns
- **Rule-based labeling** with state machine constraints
- **TensorFlow Lite export** for Raspberry Pi deployment

### Detected Phases
- **IDLE**: < 15W (standby)
- **WASHING**: 15-180W (washing, filling, agitation)
- **RINSE**: 180-280W (drain/refill cycles with spikes)
- **SPIN**: > 280W (high-speed spinning)

For detailed documentation, see:
- `ml/README.md` - Complete ML pipeline documentation
- `ml/QUICKSTART.md` - 3-step training guide

## Related Repositories

- **iot-RPI-MQTT-broker**: Raspberry Pi monitoring scripts
- **iot-laundry-frontend**: Vercel frontend dashboard (https://www.iotwasher.com)

## License

ISC
