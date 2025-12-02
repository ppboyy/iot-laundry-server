# Power Anomaly Detector - AWS Lambda Deployment Guide

Complete guide to deploy the power anomaly detection Lambda function with email alerts.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Node.js 18+** installed
4. **Amazon SES** verified email addresses

## Step 1: Verify Email Addresses in Amazon SES

Before deploying, you must verify email addresses in Amazon SES.

### 1.1 Navigate to Amazon SES Console
```
AWS Console → Amazon SES → Verified identities
```

### 1.2 Verify FROM Email Address
```bash
# Replace with your domain email
FROM_EMAIL=alerts@iotwasher.com

# Via AWS Console:
1. Click "Create identity"
2. Select "Email address"
3. Enter: alerts@iotwasher.com
4. Click "Create identity"
5. Check your inbox and click verification link
```

### 1.3 Verify TO Email Address (Business Owner)
```bash
# Replace with business owner email
TO_EMAIL=owner@yourbusiness.com

# Repeat verification process for TO email
```

### 1.4 Move Out of SES Sandbox (For Production)
In SES sandbox mode, you can only send to verified addresses. To send to any address:

```bash
AWS Console → Amazon SES → Account dashboard → Request production access
```

Fill out the request form (usually approved within 24 hours).

## Step 2: Configure the Lambda Function

Edit `power-anomaly-detector.js` and update the CONFIG section:

```javascript
const CONFIG = {
  // Power thresholds (adjust based on your machines)
  NORMAL_MAX: 750,
  WARNING_THRESHOLD: 800,
  CRITICAL_THRESHOLD: 1000,
  
  // Email configuration - UPDATE THESE
  SES_REGION: 'ap-southeast-1',          // Your AWS region
  FROM_EMAIL: 'alerts@iotwasher.com',    // Verified sender
  TO_EMAIL: 'owner@yourbusiness.com',    // Verified recipient
  
  // Alert cooldown
  COOLDOWN_MINUTES: 15,
};
```

## Step 3: Test Locally

```bash
cd lambda

# Install dependencies
npm install

# Run local tests
node test-lambda.js
```

Expected output:
```
🧪 Testing Power Anomaly Detector Lambda
============================================================

📋 Test 1: Normal Power (should not trigger)
------------------------------------------------------------
Input: { ... }
✅ Result: { "statusCode": 200, "body": "..." }
...
```

## Step 4: Package the Lambda Function

### 4.1 Install Production Dependencies
```bash
cd lambda
npm install --production
```

### 4.2 Create Deployment Package

**Windows (PowerShell):**
```powershell
Compress-Archive -Path power-anomaly-detector.js,node_modules,package.json -DestinationPath power-anomaly-detector.zip -Force
```

**Linux/Mac:**
```bash
zip -r power-anomaly-detector.zip power-anomaly-detector.js node_modules package.json
```

The zip file should be around 500KB-1MB.

## Step 5: Create IAM Role for Lambda

### 5.1 Create Trust Policy File
Create `trust-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 5.2 Create IAM Role
```bash
aws iam create-role \
  --role-name PowerAnomalyDetectorRole \
  --assume-role-policy-document file://trust-policy.json
```

### 5.3 Attach Policies
```bash
# Basic Lambda execution
aws iam attach-role-policy \
  --role-name PowerAnomalyDetectorRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# SES send email permission
aws iam put-role-policy \
  --role-name PowerAnomalyDetectorRole \
  --policy-name SESSendEmailPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ],
        "Resource": "*"
      }
    ]
  }'
```

### 5.4 Get Role ARN
```bash
aws iam get-role --role-name PowerAnomalyDetectorRole --query 'Role.Arn' --output text
```

Save this ARN, you'll need it in the next step.

## Step 6: Deploy Lambda Function

### 6.1 Create Lambda Function
```bash
# Replace with your account ID and region
ROLE_ARN="arn:aws:iam::YOUR_ACCOUNT_ID:role/PowerAnomalyDetectorRole"
REGION="ap-southeast-1"

aws lambda create-function \
  --function-name PowerAnomalyDetector \
  --runtime nodejs18.x \
  --role $ROLE_ARN \
  --handler power-anomaly-detector.handler \
  --zip-file fileb://power-anomaly-detector.zip \
  --timeout 30 \
  --memory-size 256 \
  --region $REGION \
  --description "Detects power anomalies and sends email alerts"
```

### 6.2 Verify Deployment
```bash
aws lambda get-function --function-name PowerAnomalyDetector --region $REGION
```

### 6.3 Get Lambda ARN
```bash
aws lambda get-function \
  --function-name PowerAnomalyDetector \
  --region $REGION \
  --query 'Configuration.FunctionArn' \
  --output text
```

Save this ARN for the IoT Rule configuration.

## Step 7: Test Lambda Function

### 7.1 Create Test Event
Create `test-event.json`:
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

### 7.2 Invoke Lambda
```bash
aws lambda invoke \
  --function-name PowerAnomalyDetector \
  --payload file://test-event.json \
  --region $REGION \
  response.json

cat response.json
```

### 7.3 Check Your Email
You should receive an email alert at the TO_EMAIL address.

## Step 8: Create AWS IoT Core Rule

### 8.1 Update iot-rule.json
Edit `iot-rule.json` and replace `YOUR_ACCOUNT_ID` with your AWS account ID:

```json
{
  "ruleName": "PowerAnomalyDetector",
  "description": "Detect high power consumption and trigger Lambda alert",
  "sql": "SELECT * FROM 'washer/+/data' WHERE current > 750",
  "actions": [
    {
      "lambda": {
        "functionArn": "arn:aws:lambda:ap-southeast-1:YOUR_ACCOUNT_ID:function:PowerAnomalyDetector"
      }
    }
  ],
  "ruleDisabled": false,
  "awsIotSqlVersion": "2016-03-23"
}
```

### 8.2 Create IoT Rule
```bash
aws iot create-topic-rule \
  --rule-name PowerAnomalyDetector \
  --topic-rule-payload file://iot-rule.json \
  --region $REGION
```

### 8.3 Grant IoT Permission to Invoke Lambda
```bash
FUNCTION_ARN="arn:aws:lambda:ap-southeast-1:YOUR_ACCOUNT_ID:function:PowerAnomalyDetector"

aws lambda add-permission \
  --function-name PowerAnomalyDetector \
  --statement-id IoTInvokeLambda \
  --action lambda:InvokeFunction \
  --principal iot.amazonaws.com \
  --source-arn "arn:aws:iot:$REGION:YOUR_ACCOUNT_ID:rule/PowerAnomalyDetector" \
  --region $REGION
```

### 8.4 Verify IoT Rule
```bash
aws iot get-topic-rule --rule-name PowerAnomalyDetector --region $REGION
```

## Step 9: Monitor and Test

### 9.1 View CloudWatch Logs
```bash
aws logs tail /aws/lambda/PowerAnomalyDetector --follow --region $REGION
```

### 9.2 Test with Real Data
From your Raspberry Pi, publish high power data to trigger the alert:

```bash
# This should trigger an alert if power > 750W
mosquitto_pub -h localhost -t "WM-01/test" -m '{
  "MachineID": "WM-01",
  "current": 900.0,
  "state": "RUNNING",
  "ml_phase": "SPIN",
  "timestamp": "2025-12-02T12:00:00Z"
}'
```

Wait 30 seconds for your monitor to publish to AWS IoT Core, or manually trigger from IoT Console.

### 9.3 Check Metrics
```bash
# AWS Console → Lambda → PowerAnomalyDetector → Monitor
# View: Invocations, Duration, Errors, Success rate
```

## Step 10: Update Lambda Function (After Changes)

```bash
# Make changes to power-anomaly-detector.js
# Reinstall dependencies if needed
npm install --production

# Repackage
# Windows:
Compress-Archive -Path power-anomaly-detector.js,node_modules,package.json -DestinationPath power-anomaly-detector.zip -Force

# Linux/Mac:
zip -r power-anomaly-detector.zip power-anomaly-detector.js node_modules package.json

# Update function
aws lambda update-function-code \
  --function-name PowerAnomalyDetector \
  --zip-file fileb://power-anomaly-detector.zip \
  --region $REGION
```

## Troubleshooting

### Email Not Sending
```bash
# Check SES verification status
aws ses get-identity-verification-attributes \
  --identities alerts@iotwasher.com owner@yourbusiness.com \
  --region $REGION

# Check CloudWatch logs for errors
aws logs tail /aws/lambda/PowerAnomalyDetector --follow --region $REGION
```

### Lambda Not Triggering
```bash
# Check IoT Rule SQL - test in IoT Console
AWS Console → IoT Core → Act → Rules → PowerAnomalyDetector → Edit → Test

# Verify permission
aws lambda get-policy --function-name PowerAnomalyDetector --region $REGION
```

### High AWS Costs
```bash
# Monitor invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=PowerAnomalyDetector \
  --start-time 2025-12-01T00:00:00Z \
  --end-time 2025-12-02T00:00:00Z \
  --period 3600 \
  --statistics Sum \
  --region $REGION

# Adjust cooldown period in CONFIG if too many alerts
```

## Cost Estimation

**Free Tier (Monthly)**:
- Lambda: 1M requests, 400,000 GB-seconds
- SES: 62,000 emails (when sending from EC2)
- CloudWatch Logs: 5GB ingestion

**Typical Usage** (4 machines, 1 alert/day):
- Lambda invocations: ~120/month (only when power > 750W)
- SES emails: ~120/month
- Cost: **$0.00** (within free tier)

**Heavy Usage** (10 alerts/day):
- Lambda: ~300/month
- SES: ~300/month
- Cost: **$0.00** (still within free tier)

## Production Recommendations

1. **Use DynamoDB for Cooldown**: Replace in-memory Map with DynamoDB table
2. **Add SNS**: Send alerts to SNS topic for SMS/push notifications
3. **Add Dashboard Link**: Include direct link to machine in email
4. **Customize Thresholds**: Different thresholds per machine type
5. **Add Historical Data**: Include power trend graph in email
6. **Multiple Recipients**: Support distribution lists
7. **Alert Escalation**: Send to different people based on severity

## Security Best Practices

1. ✅ Use IAM roles (not access keys)
2. ✅ Minimize Lambda permissions (only SES send)
3. ✅ Verify SES email addresses
4. ✅ Enable CloudWatch logging
5. ✅ Set Lambda timeout (30 seconds)
6. ✅ Use environment variables for sensitive config
7. ✅ Encrypt environment variables with KMS

## Next Steps

- [ ] Deploy Lambda function
- [ ] Verify email addresses in SES
- [ ] Test with sample data
- [ ] Create IoT rule
- [ ] Monitor CloudWatch logs
- [ ] Test with real washing machine data
- [ ] Adjust thresholds based on false positive rate
- [ ] Set up CloudWatch alarms for Lambda errors
