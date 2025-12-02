/**
 * Local test script for Power Anomaly Detector Lambda
 * 
 * Run: node test-lambda.js
 */

// Mock AWS SDK for local testing
const mockSES = {
  send: async (command) => {
    console.log('\n📧 [MOCK] Email would be sent with:');
    console.log('  From:', command.input.Source);
    console.log('  To:', command.input.Destination.ToAddresses.join(', '));
    console.log('  Subject:', command.input.Message.Subject.Data);
    console.log('  HTML Body Length:', command.input.Message.Body.Html.Data.length, 'chars');
    return { MessageId: 'mock-message-id-12345' };
  }
};

// Mock the AWS SDK module
const Module = require('module');
const originalRequire = Module.prototype.require;

Module.prototype.require = function(id) {
  if (id === '@aws-sdk/client-ses') {
    return {
      SESClient: class MockSESClient {
        constructor(config) {
          console.log('📧 Mock SES Client initialized with region:', config.region);
        }
      },
      SendEmailCommand: class MockSendEmailCommand {
        constructor(params) {
          this.input = params;
        }
      }
    };
  }
  return originalRequire.apply(this, arguments);
};

// Load the Lambda function
const lambda = require('./power-anomaly-detector.js');

// Override sesClient with mock
const { SESClient } = require('@aws-sdk/client-ses');
lambda.sesClient = mockSES;

// Test cases
const testCases = [
  {
    name: 'Normal Power (should not trigger)',
    event: {
      MachineID: 'WM-01',
      current: 250.5,
      state: 'RUNNING',
      ml_phase: 'WASHING',
      ml_confidence: 0.87,
      timestamp: new Date().toISOString(),
      cycle_number: 5,
      door_opened: false
    }
  },
  {
    name: 'Warning Level Power (800W)',
    event: {
      MachineID: 'WM-02',
      current: 850.0,
      state: 'RUNNING',
      ml_phase: 'SPIN',
      ml_confidence: 0.92,
      timestamp: new Date().toISOString(),
      cycle_number: 12,
      door_opened: false
    }
  },
  {
    name: 'Critical Level Power (1100W)',
    event: {
      MachineID: 'WM-03',
      current: 1100.0,
      state: 'RUNNING',
      ml_phase: 'SPIN',
      ml_confidence: 0.78,
      timestamp: new Date().toISOString(),
      cycle_number: 8,
      door_opened: false
    }
  },
  {
    name: 'Invalid Data (missing fields)',
    event: {
      MachineID: 'WM-04',
      state: 'RUNNING'
      // Missing 'current' field
    }
  }
];

// Run tests
async function runTests() {
  console.log('🧪 Testing Power Anomaly Detector Lambda\n');
  console.log('='.repeat(60));
  
  for (let i = 0; i < testCases.length; i++) {
    const testCase = testCases[i];
    console.log(`\n📋 Test ${i + 1}: ${testCase.name}`);
    console.log('-'.repeat(60));
    console.log('Input:', JSON.stringify(testCase.event, null, 2));
    
    try {
      const result = await lambda.handler(testCase.event);
      console.log('\n✅ Result:', JSON.stringify(result, null, 2));
    } catch (error) {
      console.log('\n❌ Error:', error.message);
    }
    
    console.log('='.repeat(60));
  }
  
  console.log('\n✨ All tests completed!\n');
  console.log('📝 Notes:');
  console.log('  - Email sending is mocked for local testing');
  console.log('  - Deploy to AWS to test actual SES integration');
  console.log('  - Update CONFIG in power-anomaly-detector.js with your email addresses');
  console.log('  - Verify email addresses in Amazon SES before deployment\n');
}

// Run the tests
runTests().catch(console.error);
