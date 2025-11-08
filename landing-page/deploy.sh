#!/bin/bash

# Data Destroyer - Vercel Deployment Script
# This script will deploy your landing page to Vercel

echo "=========================================="
echo "Data Destroyer - Vercel Deployment"
echo "=========================================="
echo ""

cd /home/user/datadestroyer/landing-page

echo "Step 1: Logging into Vercel..."
echo "A browser window will open for you to login."
echo "Please login with your Vercel account."
echo ""

vercel login

echo ""
echo "Step 2: Deploying to Vercel..."
echo ""

# Deploy to production
vercel --prod --yes

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Your landing page is now live!"
echo "Check the URL above to see your deployed site."
echo ""
