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
    const event = req.body;
    console.log(`Stripe webhook: ${event.type}`);

    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object;
        const license_key = session.metadata?.license_key || session.client_reference_id;
        const email = session.customer_email || '';
        const expires_at = new Date(Date.now() + 30 * 86400000).toISOString();

        if (license_key) {
          // Update existing pending license to active
          const resp = await supabaseFetch(
            `forge_licenses?license_key=eq.${license_key}`,
            {
              method: 'PATCH',
              body: JSON.stringify({
                status: 'active',
                expires_at,
                email,
                stripe_subscription_id: session.subscription,
                stripe_customer_id: session.customer,
              }),
            }
          );
          console.log(`License activated: ${license_key} for ${email}`);
        } else {
          // Fallback: create new license
          const new_key = 'fg_' + crypto.randomBytes(24).toString('hex');
          await supabaseFetch('forge_licenses', {
            method: 'POST',
            body: JSON.stringify({
              license_key: new_key,
              tier: session.metadata?.tier || 'individual',
              status: 'active',
              expires_at,
              email,
              stripe_subscription_id: session.subscription,
              stripe_customer_id: session.customer,
            }),
          });
          console.log(`License created (fallback): ${new_key}`);
        }
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
      default:
        console.log(`Unhandled: ${event.type}`);
    }

    return res.status(200).json({ received: true });
  } catch (err) {
    console.error('Webhook error:', err);
    return res.status(500).json({ error: err.message });
  }
};
