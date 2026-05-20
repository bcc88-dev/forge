// POST /api/license/validate - Validates a license key
// Vercel serverless function

const crypto = require('crypto');

// In-memory store for demo. In production: use Supabase or KV.
const VALID_KEYS = new Map();

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { key } = req.body || {};
    if (!key) {
      return res.status(400).json({ error: 'License key required' });
    }

    // Demo keys for testing
    const DEMO_KEYS = {
      'demo_individual': { tier: 'individual', expires: '2027-01-01T00:00:00Z' },
      'demo_pro': { tier: 'pro', expires: '2027-01-01T00:00:00Z' },
    };

    const stored = VALID_KEYS.get(key) || DEMO_KEYS[key];
    if (!stored) {
      return res.status(200).json({ valid: false, error: 'Invalid license key' });
    }

    const now = new Date();
    const expires = new Date(stored.expires);
    if (now > expires) {
      return res.status(200).json({ valid: false, error: 'License expired' });
    }

    return res.status(200).json({
      valid: true,
      tier: stored.tier,
      expires_at: stored.expires
    });
  } catch (err) {
    console.error('Validate error:', err);
    return res.status(500).json({ error: err.message });
  }
};
