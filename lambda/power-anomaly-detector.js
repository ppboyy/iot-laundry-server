/**
 * AWS Lambda Function: Power Anomaly Detector
 * 
 * Monitors washing machine power consumption and sends email alerts
 * via Amazon SES when unusually high power is detected.
 * 
 * Triggers: AWS IoT Core Rule on topic: washer/+/data
 */

const { SESClient, SendEmailCommand } = require('@aws-sdk/client-ses');

// Configuration
const CONFIG = {
  // Power thresholds (in Watts)
  NORMAL_MAX: 750,        // Normal maximum during spin cycle
  WARNING_THRESHOLD: 800, // Send warning above this
  CRITICAL_THRESHOLD: 1000, // Critical alert level
  
  // Email configuration
  SES_REGION: 'ap-southeast-1', // Change to your SES region
  FROM_EMAIL: 'alerts@iotwasher.com', // Must be verified in SES
  TO_EMAIL: 'owner@yourbusiness.com', // Business owner email
  
  // Alert cooldown (prevent spam)
  COOLDOWN_MINUTES: 15,
};

// In-memory cache for alert cooldown (use DynamoDB for production)
const alertCache = new Map();

// Initialize SES client
const sesClient = new SESClient({ region: CONFIG.SES_REGION });

/**
 * Lambda handler function
 */
exports.handler = async (event) => {
  console.log('Received event:', JSON.stringify(event, null, 2));
  
  try {
    // Parse incoming data from IoT Core
    const data = event;
    const machineId = data.MachineID;
    const currentPower = data.current;
    const timestamp = data.timestamp;
    const state = data.state;
    const mlPhase = data.ml_phase || 'UNKNOWN';
    
    // Validate data
    if (!machineId || currentPower === undefined) {
      console.log('Invalid data format - missing required fields');
      return {
        statusCode: 400,
        body: JSON.stringify({ message: 'Invalid data format' })
      };
    }
    
    console.log(`Machine ${machineId}: ${currentPower}W (State: ${state}, Phase: ${mlPhase})`);
    
    // Check if power is within normal range
    if (currentPower <= CONFIG.NORMAL_MAX) {
      console.log('Power level normal');
      return {
        statusCode: 200,
        body: JSON.stringify({ message: 'Power level normal' })
      };
    }
    
    // Check cooldown period
    const cacheKey = `${machineId}-anomaly`;
    const lastAlert = alertCache.get(cacheKey);
    const now = Date.now();
    
    if (lastAlert && (now - lastAlert) < CONFIG.COOLDOWN_MINUTES * 60 * 1000) {
      const minutesRemaining = Math.ceil((CONFIG.COOLDOWN_MINUTES * 60 * 1000 - (now - lastAlert)) / 60000);
      console.log(`Alert cooldown active - ${minutesRemaining} minutes remaining`);
      return {
        statusCode: 200,
        body: JSON.stringify({ 
          message: 'Alert suppressed - cooldown active',
          minutesRemaining 
        })
      };
    }
    
    // Determine severity level
    let severity = 'WARNING';
    let severityColor = '#FF9800'; // Orange
    
    if (currentPower >= CONFIG.CRITICAL_THRESHOLD) {
      severity = 'CRITICAL';
      severityColor = '#F44336'; // Red
    }
    
    // Send email alert
    const emailSent = await sendEmailAlert({
      machineId,
      currentPower,
      timestamp,
      state,
      mlPhase,
      severity,
      severityColor
    });
    
    if (emailSent) {
      // Update cooldown cache
      alertCache.set(cacheKey, now);
      
      return {
        statusCode: 200,
        body: JSON.stringify({ 
          message: 'Alert sent successfully',
          severity,
          power: currentPower
        })
      };
    } else {
      return {
        statusCode: 500,
        body: JSON.stringify({ message: 'Failed to send alert' })
      };
    }
    
  } catch (error) {
    console.error('Error processing event:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ 
        message: 'Error processing event',
        error: error.message 
      })
    };
  }
};

/**
 * Send email alert via Amazon SES
 */
async function sendEmailAlert(alertData) {
  const { machineId, currentPower, timestamp, state, mlPhase, severity, severityColor } = alertData;
  
  const subject = `⚠️ ${severity}: High Power Detected on ${machineId}`;
  
  const htmlBody = `
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .header { background-color: ${severityColor}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }
    .content { background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; }
    .metric { margin: 10px 0; padding: 10px; background-color: white; border-left: 4px solid ${severityColor}; }
    .metric-label { font-weight: bold; color: #666; }
    .metric-value { font-size: 18px; color: #333; }
    .footer { margin-top: 20px; padding: 15px; background-color: #f0f0f0; font-size: 12px; color: #666; }
    .critical { color: #F44336; font-weight: bold; }
    .warning { color: #FF9800; font-weight: bold; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2 style="margin: 0;">⚠️ Power Anomaly Alert</h2>
      <p style="margin: 5px 0 0 0;">IoT Laundry Monitoring System</p>
    </div>
    
    <div class="content">
      <p>A power anomaly has been detected on one of your washing machines.</p>
      
      <div class="metric">
        <div class="metric-label">Machine ID</div>
        <div class="metric-value">${machineId}</div>
      </div>
      
      <div class="metric">
        <div class="metric-label">Current Power Consumption</div>
        <div class="metric-value ${severity === 'CRITICAL' ? 'critical' : 'warning'}">
          ${currentPower.toFixed(1)} W
        </div>
      </div>
      
      <div class="metric">
        <div class="metric-label">Severity Level</div>
        <div class="metric-value ${severity === 'CRITICAL' ? 'critical' : 'warning'}">
          ${severity}
        </div>
      </div>
      
      <div class="metric">
        <div class="metric-label">Machine State</div>
        <div class="metric-value">${state}</div>
      </div>
      
      <div class="metric">
        <div class="metric-label">Detected Phase (ML)</div>
        <div class="metric-value">${mlPhase}</div>
      </div>
      
      <div class="metric">
        <div class="metric-label">Timestamp</div>
        <div class="metric-value">${new Date(timestamp).toLocaleString()}</div>
      </div>
      
      <h3>Recommended Actions:</h3>
      <ul>
        <li><strong>Check the machine immediately</strong> - High power consumption may indicate a malfunction</li>
        <li><strong>Inspect for overloading</strong> - Excessive load can cause motor strain</li>
        <li><strong>Verify drum rotation</strong> - Blocked drum can cause high power draw</li>
        <li><strong>Contact maintenance</strong> - If problem persists, schedule service</li>
      </ul>
      
      <h3>Normal Power Ranges:</h3>
      <ul>
        <li>IDLE: &lt;10W</li>
        <li>WASHING: 200-220W</li>
        <li>RINSE: 100-150W</li>
        <li>SPIN: 300-750W (Normal maximum)</li>
        <li>⚠️ WARNING: &gt;${CONFIG.WARNING_THRESHOLD}W</li>
        <li>🚨 CRITICAL: &gt;${CONFIG.CRITICAL_THRESHOLD}W</li>
      </ul>
    </div>
    
    <div class="footer">
      <p><strong>Dashboard:</strong> <a href="https://www.iotwasher.com">https://www.iotwasher.com</a></p>
      <p>This is an automated alert from your IoT Laundry Monitoring System.</p>
      <p>You will not receive another alert for this machine for ${CONFIG.COOLDOWN_MINUTES} minutes.</p>
    </div>
  </div>
</body>
</html>
  `.trim();
  
  const textBody = `
POWER ANOMALY ALERT - ${severity}

Machine ID: ${machineId}
Current Power: ${currentPower.toFixed(1)} W
Severity: ${severity}
State: ${state}
ML Phase: ${mlPhase}
Timestamp: ${new Date(timestamp).toLocaleString()}

RECOMMENDED ACTIONS:
- Check the machine immediately
- Inspect for overloading
- Verify drum rotation
- Contact maintenance if problem persists

Normal Power Ranges:
- IDLE: <10W
- WASHING: 200-220W
- RINSE: 100-150W
- SPIN: 300-750W (Normal maximum)
- WARNING: >${CONFIG.WARNING_THRESHOLD}W
- CRITICAL: >${CONFIG.CRITICAL_THRESHOLD}W

Dashboard: https://www.iotwasher.com

You will not receive another alert for this machine for ${CONFIG.COOLDOWN_MINUTES} minutes.
  `.trim();
  
  const params = {
    Source: CONFIG.FROM_EMAIL,
    Destination: {
      ToAddresses: [CONFIG.TO_EMAIL]
    },
    Message: {
      Subject: {
        Data: subject,
        Charset: 'UTF-8'
      },
      Body: {
        Text: {
          Data: textBody,
          Charset: 'UTF-8'
        },
        Html: {
          Data: htmlBody,
          Charset: 'UTF-8'
        }
      }
    }
  };
  
  try {
    const command = new SendEmailCommand(params);
    const response = await sesClient.send(command);
    console.log('Email sent successfully:', response.MessageId);
    return true;
  } catch (error) {
    console.error('Error sending email:', error);
    return false;
  }
}
