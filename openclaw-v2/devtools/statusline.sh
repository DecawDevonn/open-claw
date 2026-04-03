#!/bin/bash
# Standalone version of the statusline script (same logic as used by setup_claude.sh)
input=$(cat)

tokens=$(echo "$input" | jq -r '.contextUsagePercentage // 0')
cost=$(echo "$input" | jq -r '.sessionCost // 0')
mode=$(echo "$input" | jq -r '.mode // "Normal"')

if (( $(echo "$tokens > 75" | bc -l) )); then 
    COLOR="\033[31m"
else 
    COLOR="\033[32m"
fi

printf "${COLOR}[$mode] 🪙 ${tokens}%% | 💸 \$${cost}\033[0m"
