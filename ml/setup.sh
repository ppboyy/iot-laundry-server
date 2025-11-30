#!/bin/bash
# ML Training Setup Script for EC2/Linux

echo "=========================================="
echo "Washing Machine ML - Training Setup"
echo "=========================================="

# Check Python version
echo ""
echo "Checking Python version..."
python3 --version

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy training data:"
echo "   scp power_log_gus.csv ec2:/home/ubuntu/iot-laundry-server/ml/data/power_log_raw.csv"
echo ""
echo "2. Activate environment:"
echo "   source venv/bin/activate"
echo ""
echo "3. Prepare data:"
echo "   python training/prepare_data.py"
echo ""
echo "4. Train model:"
echo "   python training/train_random_forest.py"
echo ""
