#!/bin/bash

# Script to upgrade the subscription_plans module

echo "Upgrading subscription_plans module..."

# Navigate to Odoo directory
cd /home/dell/Documents/Projects/diago-odoo/odoo-16.0

# Stop Odoo if running
echo "Stopping Odoo..."
pkill -f "python.*odoo"

# Wait a moment
sleep 2

# Upgrade the module
echo "Upgrading module..."
python3 odoo-bin -d diago_db -u subscription_plans --stop-after-init

echo "Module upgrade completed!"
echo "You can now restart Odoo normally."
