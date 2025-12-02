# AWS Lambda - Power Anomaly Detector

Monitors washing machine power consumption and sends email alerts when unusually high power is detected.

## Overview

This Lambda function is triggered by AWS IoT Core when power consumption exceeds 750W. It sends formatted email alerts via Amazon SES to notify the business owner of potential equipment issues.

## Features

- ⚡ **Real-time Monitoring**: Triggers automatically via IoT Core rule
- 📧 **Email Alerts**: Professional HTML/text emails via Amazon SES
- 🎯 **Severity Levels**: WARNING (800W+) and CRITICAL (1000W+)
- ⏱️ **Alert Cooldown**: 15-minute cooldown prevents email spam
- 🎨 **Rich Formatting**: Color-coded severity indicators
- 📊 **Detailed Context**: Includes state, ML phase, timestamp
- 💡 **Actionable Insights**: Recommends troubleshooting steps

## Architecture

```
Raspberry Pi → AWS IoT Core → IoT Rule (power > 750W) 
                                    ↓
                            Lambda Function
                                    ↓
                            Amazon SES → Email Alert
```

## Configuration

### Power Thresholds
- **NORMAL_MAX**: 750W (typical maximum during spin)
- **WARNING_THRESHOLD**: 800W (sends warning email)
- **CRITICAL_THRESHOLD**: 1000W (sends critical email)

### Email Settings
- **FROM_EMAIL**: Must be verified in Amazon SES
- **TO_EMAIL**: Business owner email (must be verified in sandbox mode)
- **SES_REGION**: AWS region where SES is configured

### Alert Cooldown
- **COOLDOWN_MINUTES**: 15 minutes between alerts per machine

## Files

- `power-anomaly-detector.js` - Main Lambda function
- `iot-rule.json` - AWS IoT Core rule configuration
- `package.json` - Node.js dependencies
- `test-lambda.js` - Local testing script
- `DEPLOYMENT.md` - Complete deployment guide

## Quick Start

### 1. Install Dependencies
```bash
cd lambda
npm install
```

### 2. Test Locally
```bash
node test-lambda.js
```

### 3. Configure
Edit `power-anomaly-detector.js`:
```javascript
const CONFIG = {
  SES_REGION: 'ap-southeast-1',
  FROM_EMAIL: 'alerts@iotwasher.com',  // Change this
  TO_EMAIL: 'owner@yourbusiness.com',  // Change this
  WARNING_THRESHOLD: 800,
  CRITICAL_THRESHOLD: 1000,
  COOLDOWN_MINUTES: 15
};
```

### 4. Deploy to AWS
See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment instructions.

## Email Alert Example

**Subject**: ⚠️ WARNING: High Power Detected on WM-01

**Body Includes**:
- Machine ID and current state
- Power consumption with severity color
- ML-detected phase
- Timestamp
- Recommended actions
- Normal power ranges reference
- Link to dashboard

## IoT Rule SQL

The Lambda is triggered by this IoT Core rule:

```sql
SELECT * FROM 'washer/+/data' WHERE current > 750
```

This filters messages to only invoke Lambda when power exceeds 750W.

## Data Format

Expected input from IoT Core:
```json
{
  "MachineID": "WM-01",
  "current": 850.0,
  "state": "RUNNING",
  "ml_phase": "SPIN",
  "ml_confidence": 0.92,
  "timestamp": "2025-12-02T12:00:00.000Z",
  "cycle_number": 5,
  "door_opened": false
}
```

## Response Format

Success response:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Alert sent successfully",
    "severity": "WARNING",
    "power": 850.0
  }
}
```

Cooldown active:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Alert suppressed - cooldown active",
    "minutesRemaining": 12
  }
}
```

## Testing

### Local Testing
```bash
node test-lambda.js
```

This runs 4 test cases:
1. Normal power (no alert)
2. Warning level (800W)
3. Critical level (1100W)
4. Invalid data

### AWS Testing
```bash
# Create test event
aws lambda invoke \
  --function-name PowerAnomalyDetector \
  --payload '{"MachineID":"WM-01","current":900.0,"state":"RUNNING"}' \
  response.json

cat response.json
```

## Monitoring

### CloudWatch Logs
```bash
aws logs tail /aws/lambda/PowerAnomalyDetector --follow
```

### Metrics to Monitor
- **Invocations**: Number of times triggered
- **Errors**: Failed executions
- **Duration**: Execution time (should be <1000ms)
- **Throttles**: Rate limiting (should be 0)

### CloudWatch Alarms
Set up alarms for:
- Error rate > 5%
- Duration > 5 seconds
- Throttles > 0

## Troubleshooting

### Email Not Received
1. Check SES email verification
2. Check spam folder
3. Verify FROM_EMAIL and TO_EMAIL in code
4. Check CloudWatch logs for errors
5. Verify SES region matches Lambda region

### Lambda Not Triggering
1. Check IoT Rule is enabled
2. Verify SQL query syntax
3. Test rule in IoT Console
4. Check Lambda permissions
5. Verify machine is publishing to correct topic

### Too Many Emails
1. Increase COOLDOWN_MINUTES
2. Adjust WARNING_THRESHOLD higher
3. Check for faulty sensor readings
4. Review IoT Rule SQL filter

### High Costs
- Lambda: ~$0.20 per 1M invocations (after free tier)
- SES: $0.10 per 1,000 emails (after free tier)
- CloudWatch: $0.50 per GB logs

Typical monthly cost: **$0.00** (within free tier for normal usage)

## Customization Ideas

### Add SMS Alerts
```javascript
// Use SNS for SMS
const { SNSClient, PublishCommand } = require('@aws-sdk/client-sns');
// Send SMS for CRITICAL alerts only
```

### Machine-Specific Thresholds
```javascript
const THRESHOLDS = {
  'WM-01': { warning: 800, critical: 1000 },
  'WM-02': { warning: 750, critical: 950 },
  // Industrial machines
  'WM-05': { warning: 1200, critical: 1500 }
};
```

### Add Trend Analysis
```javascript
// Query last 10 readings from DynamoDB
// Include power trend graph in email
// Detect gradual increase over time
```

### Multiple Recipients
```javascript
const TO_EMAILS = {
  WARNING: ['manager@company.com'],
  CRITICAL: ['manager@company.com', 'oncall@company.com', 'owner@company.com']
};
```

### Slack Integration
```javascript
// Send alerts to Slack webhook
// Include direct link to machine dashboard
// Tag relevant team members
```

## Security Considerations

1. ✅ **IAM Roles**: Function uses role-based permissions
2. ✅ **Minimal Permissions**: Only SES:SendEmail and CloudWatch
3. ✅ **Verified Emails**: SES requires verification
4. ✅ **No Hardcoded Secrets**: Use environment variables or Secrets Manager
5. ✅ **Input Validation**: Checks for required fields
6. ✅ **Rate Limiting**: Cooldown prevents abuse

## Production Checklist

- [ ] Verify FROM_EMAIL in Amazon SES
- [ ] Verify TO_EMAIL in Amazon SES (or move out of sandbox)
- [ ] Update CONFIG with correct email addresses
- [ ] Test locally with `node test-lambda.js`
- [ ] Deploy to AWS Lambda
- [ ] Create and enable IoT Core rule
- [ ] Grant IoT permission to invoke Lambda
- [ ] Test with real washing machine data
- [ ] Set up CloudWatch alarms
- [ ] Monitor logs for first 24 hours
- [ ] Adjust thresholds based on false positive rate
- [ ] Document escalation procedures

## Support

For issues or questions:
1. Check [DEPLOYMENT.md](./DEPLOYMENT.md) for setup help
2. Review CloudWatch logs
3. Test with `test-lambda.js` locally
4. Verify SES configuration
5. Check IoT Core rule configuration

## License

ISC
