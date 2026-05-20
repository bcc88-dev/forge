const crypto = require('crypto');

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

async function supabaseFetch(path, options = {}) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) return null;
  const resp = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'apikey': SUPABASE_SERVICE_KEY,
      'Authorization': `Bearer ${SUPABASE_SERVICE_KEY}`,
      'Prefer': 'return=minimal',
      ...options.headers,
    },
  });
  return resp;
}

module.exports = async (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const sig = req.headers['stripe-signature'];
    const body = JSON.stringify(req.body);
    const event = req.body;
    console.log(`Stripe webhook: ${event.type}`);

    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object;
        const license_key = 'fg_' + crypto.randomBytes(24).toString('hex');
        const expires_at = new Date(Date.now() + 30 * 86400000).toISOString();
        await supabaseFetch('forge_licenses', {
          method: 'POST',
          body: JSON.stringify({
            license_key,
            tier: session.metadata?.tier || 'individual',
            status: 'active',
            expires_at,
            stripe_subscription_id: session.subscription,
            stripe_customer_id: session.customer,
          }),
        });
        console.log(`License created: ${license_key} for ${session.customer_email}`);
        break;
      }
      case 'customer.subscription.deleted': {
        const sub = event.data.object;
        await supabaseFetch(`forge_licenses?stripe_subscription_id=eq.${sub.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ status: 'cancelled' }),
        });
        console.log(`Subscription cancelled: ${sub.id}`);
        break;
      }
      case 'invoice.payment_succeeded':
      case 'invoice.payment_failed':
        console.log(`Invoice event: ${event.type} for ${event.data.object.id}`);
        break;
      default:
        console.log(`Unhandled: ${event.type}`);
    }

    return res.status(200).json({ received: true });
  } catch (err) {
    console.error('Webhook error:', err);
    return res.status(500).json({ error: err.message });
  }
};
