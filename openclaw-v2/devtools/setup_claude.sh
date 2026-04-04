#!/bin/bash

echo "⚙️ OpenClaw Dev Environment Setup..."

# --- GLOBAL CONFIG ---
# NOTE: this script assumes `claude` CLI is installed and available on PATH.
# It does not provide credentials or tokens; these must be configured by the dev.
claude config set max-budget-usd 10.00 || true
claude config set verbose true || true

claude config set auto-mode.ignore-patterns '[
"**/node_modules/**",
"**/dist/**",
"**/.git/**",
"**/build/**",
"**/.next/**",
"**/data/**",
"**/models/**"
]'

# --- CLAUDE IGNORE ---
cat <<'EOF' > .claudeignore
node_modules/
dist/
build/
.next/
.venv/
data/
models/
*.log
*.lock
EOF

# --- STATUS LINE ---
mkdir -p ~/.claude

cat <<'EOF' > ~/.claude/statusline.sh
#!/bin/bash
input=$(cat)

# input expected as JSON with fields: contextUsagePercentage, sessionCost, mode
tokens=$(echo "$input" | jq -r '.contextUsagePercentage // 0')
cost=$(echo "$input" | jq -r '.sessionCost // 0')
mode=$(echo "$input" | jq -r '.mode // "Normal"')

if (( $(echo "$tokens > 75" | bc -l) )); then 
    COLOR="\033[31m"
else 
    COLOR="\033[32m"
fi

printf "${COLOR}[$mode] 🪙 ${tokens}%% | 💸 \$${cost}\033[0m"
EOF

chmod +x ~/.claude/statusline.sh || true

claude config set statusLine.type command || true
claude config set statusLine.command "sh ~/.claude/statusline.sh" || true

# --- ALIASES ---
cat <<'EOF' >> ~/.zshrc

# OpenClaw Dev Workflow
alias oc-plan='claude /clear --permission-mode plan'
alias oc-batch='claude --permission-mode auto-accept -p'
alias oc-check='claude -p "/context && /cost"'
alias oc-continue='claude -c'
EOF

# Only source if running in interactive zsh
if [ -n "$ZSH_VERSION" ]; then
  source ~/.zshrc || true
fi

echo "✅ OpenClaw Dev Setup Complete"
echo "🚀 Run: oc-plan"
