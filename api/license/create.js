const crypto = require('crypto');

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { email, stripe_session_id } = req.body || {};
    if (!email || !stripe_session_id) {
      return res.status(400).json({ error: 'email and stripe_session_id required' });
    }

    let stripe = null;
    let tier = 'individual';
    if (process.env.STRIPE_SECRET_KEY) {
      const { Stripe } = require('stripe');
      stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
      const session = await stripe.checkout.sessions.retrieve(stripe_session_id);
      if (session.payment_status !== 'paid') {
        return res.status(402).json({ error: 'Payment not completed' });
      }
      tier = session.metadata?.tier || 'individual';
    }

    const license_key = 'fg_' + crypto.randomBytes(24).toString('hex');
    const expires_at = new Date(Date.now() + 30 * 86400000).toISOString();

    let stored = false;
    if (SUPABASE_URL && SUPABASE_SERVICE_KEY) {
      const body = JSON.stringify({
        license_key,
        tier,
        status: 'active',
        expires_at,
        stripe_subscription_id: stripe ? stripe_session_id : null,
        stripe_customer_id: stripe ? (await stripe.checkout.sessions.retrieve(stripe_session_id)).customer : null,
      });
      const resp = await fetch(`${SUPABASE_URL}/rest/v1/forge_licenses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': SUPABASE_SERVICE_KEY,
          'Authorization': `Bearer ${SUPABASE_SERVICE_KEY}`,
          'Prefer': 'return=minimal',
        },
        body,
      });
      stored = resp.ok;
    }

    return res.status(200).json({
      key: license_key,
      email,
      tier,
      expires_at,
      created_at: new Date().toISOString(),
      valid: true,
      stored,
    });
  } catch (err) {
    console.error('License create error:', err);
    return res.status(500).json({ error: err.message });
  }
};
