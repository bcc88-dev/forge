const Stripe = require('stripe');

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

module.exports = async (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { tier = 'individual', email } = req.body || {};
    const prices = { individual: 1500, enterprise: 3000 };
    const amount = prices[tier] || 1500;

    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      customer_email: email,
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
      metadata: { tier },
      success_url: `${req.headers.origin}/?success=true`,
      cancel_url: `${req.headers.origin}/?canceled=true`,
    });

    return res.status(200).json({ url: session.url, session_id: session.id });
  } catch (err) {
    console.error('Checkout error:', err);
    return res.status(500).json({ error: err.message });
  }
};
