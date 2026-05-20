#!/bin/bash
set -e

echo "=== Forge Vercel Deploy ==="

# Login if not already
if ! npx vercel whoami &>/dev/null; then
    echo "Please login to Vercel:"
    npx vercel login
fi

# Link project
npx vercel link --yes --repo https://github.com/bcc88-dev/forge

# Set secrets
echo "Setting environment secrets..."
npx vercel secrets add stripe_secret_key
npx vercel secrets add stripe_webhook_secret
npx vercel secrets add supabase_url
npx vercel secrets add supabase_service_key

# Deploy
npx vercel --prod --yes

echo "=== Done! ==="
