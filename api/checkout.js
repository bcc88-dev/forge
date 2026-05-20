const crypto = require('crypto');
const Stripe = require('stripe');

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

async function supabaseFetch(path, options = {}) {
  const resp = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'apikey': SUPABASE_SERVICE_KEY,
      'Authorization': `Bearer ${SUPABASE_SERVICE_KEY}`,
      ...options.headers,
    },
  });
  return resp;
}

module.exports = async (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { tier = 'individual', email } = req.body || {};
    const prices = { individual: 1500, enterprise: 3000 };
    const amount = prices[tier] || 1500;

    // Generate license key BEFORE payment
    const license_key = 'fg_' + crypto.randomBytes(24).toString('hex');

    // Insert pending license into Supabase
    await supabaseFetch('forge_licenses', {
      method: 'POST',
      body: JSON.stringify({
        license_key,
        tier,
        status: 'pending',
        email: email || '',
      }),
    });

    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      customer_email: email || undefined,
      client_reference_id: license_key,
      line_items: [{
        price_data: {
          currency: 'usd',
          product_data: {
            name: tier === 'enterprise' ? 'CLIDE Enterprise' : 'CLIDE Individual',
            description: 'AI coding agent with persistent memory',
          },
          unit_amount: amount,
          recurring: { interval: 'month' },
        },
        quantity: 1,
      }],
      metadata: { tier, license_key },
      success_url: `${req.headers.origin}/?success=true&key=${license_key}`,
      cancel_url: `${req.headers.origin}/?canceled=true`,
    });

    return res.status(200).json({
      url: session.url,
      session_id: session.id,
      license_key,
    });
  } catch (err) {
    console.error('Checkout error:', err);
    return res.status(500).json({ error: err.message });
  }
};
