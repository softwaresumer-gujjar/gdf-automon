#!/usr/bin/env bash
# Generate VAPID keys for Web Push notifications.
# Writes keys to infra/.env (creates or appends).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$INFRA_DIR/.env"

echo "=== Generating VAPID Keys for Web Push ==="

# Try web-push CLI (requires: npm install -g web-push)
if command -v web-push &>/dev/null; then
  OUTPUT=$(web-push generate-vapid-keys --json)
  PUBLIC_KEY=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['publicKey'])")
  PRIVATE_KEY=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['privateKey'])")
elif command -v npx &>/dev/null; then
  OUTPUT=$(npx --yes web-push generate-vapid-keys --json 2>/dev/null)
  PUBLIC_KEY=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['publicKey'])")
  PRIVATE_KEY=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['privateKey'])")
else
  echo "ERROR: web-push CLI not found. Install with: npm install -g web-push"
  exit 1
fi

echo ""
echo "Generated keys:"
echo "  Public:  $PUBLIC_KEY"
echo "  Private: $PRIVATE_KEY"
echo ""

# Write to .env
if [[ -f "$ENV_FILE" ]]; then
  # Update existing entries
  sed -i "s|^VAPID_PUBLIC_KEY=.*|VAPID_PUBLIC_KEY=$PUBLIC_KEY|" "$ENV_FILE"
  sed -i "s|^VAPID_PRIVATE_KEY=.*|VAPID_PRIVATE_KEY=$PRIVATE_KEY|" "$ENV_FILE"
  echo "Updated VAPID keys in $ENV_FILE"
else
  # Create .env from template
  cp "$INFRA_DIR/.env.example" "$ENV_FILE"
  sed -i "s|^VAPID_PUBLIC_KEY=.*|VAPID_PUBLIC_KEY=$PUBLIC_KEY|" "$ENV_FILE"
  sed -i "s|^VAPID_PRIVATE_KEY=.*|VAPID_PRIVATE_KEY=$PRIVATE_KEY|" "$ENV_FILE"
  echo "Created $ENV_FILE with VAPID keys"
fi

echo ""
echo "IMPORTANT: Add this to your frontend .env:"
echo "  VITE_VAPID_PUBLIC_KEY=$PUBLIC_KEY"
