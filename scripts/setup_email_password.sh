#!/bin/bash
# Setup script for configuring Sonic.net email password in postfix

set -e

echo "Sonic.net Email Configuration"
echo "=============================="
echo ""
echo "Enter your Sonic.net password (kevintmckay@sonic.net):"
read -s PASSWORD
echo ""

# Update the password file
sudo tee /etc/postfix/sasl_passwd > /dev/null <<EOF
[smtp.sonic.net]:587 kevintmckay@sonic.net:${PASSWORD}
EOF

# Secure the file
sudo chmod 600 /etc/postfix/sasl_passwd
sudo chown root:root /etc/postfix/sasl_passwd

# Create the hash database
echo "Creating password hash database..."
sudo postmap /etc/postfix/sasl_passwd

# Reload postfix
echo "Reloading postfix..."
sudo systemctl reload postfix

echo ""
echo "✓ Email configuration complete!"
echo ""
echo "To test, run:"
echo "  echo 'Test message' | mail -s 'Test Subject' kevintmckay@gmail.com"
