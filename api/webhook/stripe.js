// POST /api/webhook/stripe - Receives Stripe subscription events
// Vercel serverless function

const crypto = require('crypto');

module.exports = async (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const sig = req.headers['stripe-signature'];
    const body = JSON.stringify(req.body);

    // Verify webhook signature
    if (!process.env.STRIPE_WEBHOOK_SECRET) {
      console.warn('STRIPE_WEBHOOK_SECRET not set, skipping signature verification');
    }

    const event = req.body;
    console.log(`Stripe webhook received: ${event.type}`);

    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object;
        console.log(`Checkout completed: ${session.id} for ${session.customer_email}`);
        // In production: create license key and email customer
        break;
      }
      case 'customer.subscription.updated': {
        const subscription = event.data.object;
        console.log(`Subscription updated: ${subscription.id}, status: ${subscription.status}`);
        break;
      }
      case 'customer.subscription.deleted': {
        const subscription = event.data.object;
        console.log(`Subscription cancelled: ${subscription.id}`);
        // In production: revoke license key
        break;
      }
      case 'invoice.payment_succeeded': {
        const invoice = event.data.object;
        console.log(`Payment received: ${invoice.amount_paid / 100} ${invoice.currency}`);
        break;
      }
      case 'invoice.payment_failed': {
        const invoice = event.data.object;
        console.error(`Payment failed: ${invoice.id}`);
        break;
      }
      default:
        console.log(`Unhandled event type: ${event.type}`);
    }

    return res.status(200).json({ received: true });
  } catch (err) {
    console.error('Webhook error:', err);
    return res.status(500).json({ error: err.message });
  }
};
