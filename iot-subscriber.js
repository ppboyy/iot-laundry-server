require('dotenv').config();
const awsIot = require('aws-iot-device-sdk');
const { initializeDatabase, query } = require('./config/database');

console.log('🚀 Starting AWS IoT Core Subscriber...\n');

// Track connection state
let isConnected = false;
let messageCount = 0;
let dbReady = false;

// Initialize database connection
const startSubscriber = async () => {
    try {
        console.log('🔧 Initializing database connection...');
        await initializeDatabase();
        dbReady = true;
        console.log('✅ Database ready\n');
        
        // Create AWS IoT Device after database is ready
        const device = awsIot.device({
            keyPath: process.env.IOT_KEY_PATH,
            certPath: process.env.IOT_CERT_PATH,
            caPath: process.env.IOT_CA_PATH,
            clientId: process.env.IOT_CLIENT_ID || 'backend-subscriber',
            host: process.env.IOT_ENDPOINT
        });

        // Connection established
        device.on('connect', () => {
            isConnected = true;
            console.log('✅ Connected to AWS IoT Core!');
            console.log(`📍 Endpoint: ${process.env.IOT_ENDPOINT}`);
            console.log(`🆔 Client ID: ${process.env.IOT_CLIENT_ID || 'backend-subscriber'}\n`);
            
            // Subscribe to all washing machine data topics
            const topic = 'washer/+/data';
            device.subscribe(topic);
            console.log(`📡 Subscribed to topic: ${topic}`);
            console.log('⏳ Waiting for messages...\n');
        });

        return device;
        
    } catch (error) {
        console.error('❌ Failed to initialize:', error);
        process.exit(1);
    }
};

// Start the subscriber and get device reference
let device;
startSubscriber().then(d => {
    device = d;
    setupDeviceHandlers(device);
});

// Setup device event handlers
function setupDeviceHandlers(device) {
    // Message received from IoT Core
    device.on('message', async (topic, payload) => {
        try {
            if (!dbReady) {
                console.warn('⚠️  Database not ready, skipping message');
                return;
            }

            const data = JSON.parse(payload.toString());
            const timestamp = new Date().toISOString();
            
            messageCount++;
            console.log(`\n[${messageCount}] 📥 Received message from ${topic}`);
            console.log(`   MachineID: ${data.MachineID}`);
            console.log(`   State: ${data.state}`);
            console.log(`   Power: ${data.current}W`);
            console.log(`   Cycle: ${data.cycle_number}`);
            
            // Insert into database
            await query(
                'INSERT INTO machine_readings (data) VALUES ($1)',
                [JSON.stringify(data)]
            );
            
            console.log(`   ✅ Saved to database at ${timestamp}`);
            
        } catch (error) {
            console.error('❌ Error processing message:', error.message);
            console.error('   Topic:', topic);
            console.error('   Payload:', payload.toString());
        }
    });

    // Connection lost
    device.on('close', () => {
        if (isConnected) {
            console.log('\n⚠️  Connection to AWS IoT Core closed');
            isConnected = false;
        }
    });

    // Reconnecting
    device.on('reconnect', () => {
        console.log('🔄 Reconnecting to AWS IoT Core...');
    });

    // Connection error
    device.on('error', (error) => {
        console.error('❌ AWS IoT Core error:', error.message);
    });

    // Offline
    device.on('offline', () => {
        if (isConnected) {
            console.log('⚠️  AWS IoT Core connection offline');
            isConnected = false;
        }
    });

    // Graceful shutdown
    process.on('SIGTERM', () => {
        console.log('\n⏹️  SIGTERM received, shutting down gracefully...');
        device.end();
        process.exit(0);
    });

    process.on('SIGINT', () => {
        console.log('\n⏹️  SIGINT received, shutting down gracefully...');
        device.end();
        process.exit(0);
    });

    // Keep process alive and show stats every minute
    setInterval(() => {
        if (isConnected) {
            console.log(`\n📊 Stats: ${messageCount} messages received and processed`);
        }
    }, 60000);
}
