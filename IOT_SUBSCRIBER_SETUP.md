# AWS IoT Subscriber Setup Guide

This guide explains how to set up your EC2 server to receive data directly from AWS IoT Core.

## 📋 Prerequisites

- EC2 instance running Ubuntu
- AWS IoT Core certificates (same ones used by your Raspberry Pi)
- Node.js and npm installed

## 🔐 Step 1: Copy AWS IoT Certificates to EC2

### Option A: Using SCP (from your local machine)

If you have the certificates locally:

```bash
# Create directory on EC2
ssh ubuntu@your-ec2-ip "mkdir -p /home/ubuntu/aws-iot-certs"

# Copy certificates
scp /path/to/your/certs/private.pem.key ubuntu@your-ec2-ip:/home/ubuntu/aws-iot-certs/
scp /path/to/your/certs/certificate.pem.crt ubuntu@your-ec2-ip:/home/ubuntu/aws-iot-certs/
scp /path/to/your/certs/AmazonRootCA1.pem ubuntu@your-ec2-ip:/home/ubuntu/aws-iot-certs/
```

### Option B: Download from AWS IoT Core

On your EC2 instance:

```bash
# Create directory
mkdir -p /home/ubuntu/aws-iot-certs
cd /home/ubuntu/aws-iot-certs

# Download Amazon Root CA 1
wget https://www.amazontrust.com/repository/AmazonRootCA1.pem

# For private key and certificate, you'll need to download from AWS IoT Console
# Or copy from your Raspberry Pi if they're the same thing
```

### Set Proper Permissions

```bash
chmod 600 /home/ubuntu/aws-iot-certs/private.pem.key
chmod 644 /home/ubuntu/aws-iot-certs/certificate.pem.crt
chmod 644 /home/ubuntu/aws-iot-certs/AmazonRootCA1.pem
```

## ⚙️ Step 2: Configure Environment Variables

On your EC2 instance, edit your `.env` file:

```bash
cd /home/ubuntu/iot-laundry-server
nano .env
```

Add these lines (or update if they exist):

```env
# AWS IoT Core Configuration
IOT_ENDPOINT=a5916n61elm51-ats.iot.ap-southeast-1.amazonaws.com
IOT_CLIENT_ID=backend-subscriber
IOT_KEY_PATH=/home/ubuntu/aws-iot-certs/private.pem.key
IOT_CERT_PATH=/home/ubuntu/aws-iot-certs/certificate.pem.crt
IOT_CA_PATH=/home/ubuntu/aws-iot-certs/AmazonRootCA1.pem
```

**Important:** Update `IOT_ENDPOINT` with your actual AWS IoT Core endpoint if different.

## 📦 Step 3: Install Dependencies

```bash
cd /home/ubuntu/iot-laundry-server
npm install
```

This will install the `aws-iot-device-sdk` package.

## 🧪 Step 4: Test the Subscriber

Test that it works before running as a service:

```bash
node iot-subscriber.js
```

You should see:
```
🚀 Starting AWS IoT Core Subscriber...
✅ Connected to AWS IoT Core!
📡 Subscribed to topic: washer/+/data
⏳ Waiting for messages...
```

When your Raspberry Pi publishes data, you'll see:
```
📥 Received message from washer/WM-01/data
   MachineID: WM-01
   State: RUNNING
   Power: 245.5W
   Cycle: 3
   ✅ Saved to database
```

Press `Ctrl+C` to stop.

## 🚀 Step 5: Run as a Service with PM2

Install PM2 globally (if not already installed):

```bash
sudo npm install -g pm2
```

Start the IoT subscriber as a background service:

```bash
cd /home/ubuntu/iot-laundry-server
pm2 start iot-subscriber.js --name iot-subscriber
```

Make sure it auto-starts on reboot:

```bash
pm2 save
pm2 startup
# Run the command that PM2 outputs
```

## 📊 Step 6: Monitor the Service

Check status:
```bash
pm2 status
```

View logs:
```bash
pm2 logs iot-subscriber
```

View real-time logs:
```bash
pm2 logs iot-subscriber --lines 100
```

Restart if needed:
```bash
pm2 restart iot-subscriber
```

## 🔍 Troubleshooting

### Connection fails

**Check certificate paths:**
```bash
ls -la /home/ubuntu/aws-iot-certs/
```

**Verify .env file:**
```bash
cat /home/ubuntu/iot-laundry-server/.env | grep IOT_
```

**Test IoT endpoint connectivity:**
```bash
openssl s_client -connect a5916n61elm51-ats.iot.ap-southeast-1.amazonaws.com:8883 -CAfile /home/ubuntu/aws-iot-certs/AmazonRootCA1.pem
```

### Database insertion fails

**Check database connection:**
```bash
pm2 logs iot-subscriber --err
```

**Verify table exists:**
```bash
psql -h iot-laundry-database.chi20c6aago7.ap-southeast-1.rds.amazonaws.com -U postgres -d laundry_iot -c "\dt"
```

### Not receiving messages

**Check Raspberry Pi is publishing:**
- Verify your Pi's monitor script is running
- Check Pi's logs for publish confirmations

**Verify AWS IoT policy allows subscribing:**
- Go to AWS IoT Console → Secure → Policies
- Ensure your certificate's policy allows `iot:Subscribe` and `iot:Receive` on `washer/+/data`

## ✅ Verification

Once everything is running, you should have:

1. **API Server** - serving HTTP requests
   ```bash
   pm2 status server
   ```

2. **IoT Subscriber** - receiving data from AWS IoT Core
   ```bash
   pm2 status iot-subscriber
   ```

3. **Data flowing** - Check database:
   ```bash
   curl http://localhost:3000/api/readings?limit=5
   ```

## 🏗️ Architecture Overview

```
┌─────────────────┐
│  Raspberry Pi   │
│  (Monitor)      │
└────────┬────────┘
         │ MQTT/TLS
         ↓
┌─────────────────┐
│  AWS IoT Core   │
│  (Broker)       │
└────────┬────────┘
         │ MQTT/TLS
         ↓
┌─────────────────┐
│  EC2 Server     │
│  - iot-subscriber.js ← Receives data
│  - server.js    ← Serves API
└────────┬────────┘
         │ SQL
         ↓
┌─────────────────┐
│   AWS RDS       │
│  (PostgreSQL)   │
└─────────────────┘
```

## 📝 Notes

- The subscriber runs independently from your API server
- Both processes should be managed by PM2
- Messages are automatically inserted into the database
- The subscriber will auto-reconnect if connection drops
- Check logs regularly: `pm2 logs iot-subscriber`
