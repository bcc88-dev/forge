// POST /api/license/create - Generates a license key after Stripe payment
// Vercel serverless function

const crypto = require('crypto');
const { Stripe } = require('stripe');

module.exports = async (req, res) => {
  // CORS
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

    // Verify Stripe session
    if (!process.env.STRIPE_SECRET_KEY) {
      return res.status(500).json({ error: 'Stripe not configured' });
    }
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
    const session = await stripe.checkout.sessions.retrieve(stripe_session_id);

    if (session.payment_status !== 'paid') {
      return res.status(402).json({ error: 'Payment not completed' });
    }

    // Generate license key
    const license_key = 'fg_' + crypto.randomBytes(24).toString('hex');

    // In production: store in Supabase or KV store
    const result = {
      key: license_key,
      email,
      tier: session.metadata?.tier || 'individual',
      expires_at: new Date(Date.now() + 30 * 86400000).toISOString(),
      created_at: new Date().toISOString(),
      valid: true
    };

    return res.status(200).json(result);
  } catch (err) {
    console.error('License create error:', err);
    return res.status(500).json({ error: err.message });
  }
};
