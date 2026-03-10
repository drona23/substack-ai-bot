#!/bin/bash
# Wrapper script for launchd — activates conda then runs the bot

# Load conda
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate base

# Run the bot
cd /Users/drona23/SubstackBot
/opt/anaconda3/bin/python3 /Users/drona23/SubstackBot/daily_ai_post.py
