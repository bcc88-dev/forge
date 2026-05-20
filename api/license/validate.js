const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { key } = req.body || {};
    if (!key) return res.status(400).json({ error: 'License key required' });

    const DEMO_KEYS = {
      'demo_individual': { tier: 'individual', expires: '2027-01-01T00:00:00Z' },
      'demo_pro': { tier: 'pro', expires: '2027-01-01T00:00:00Z' },
    };
    const demo = DEMO_KEYS[key];
    if (demo) {
      const now = new Date();
      const expires = new Date(demo.expires);
      return res.status(200).json({
        valid: now <= expires,
        tier: demo.tier,
        expires_at: demo.expires,
        source: 'demo',
      });
    }

    if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
      return res.status(200).json({ valid: false, error: 'License server not configured' });
    }

    const resp = await fetch(
      `${SUPABASE_URL}/rest/v1/forge_licenses?license_key=eq.${key}&select=*&limit=1`,
      { headers: { 'apikey': SUPABASE_SERVICE_KEY, 'Authorization': `Bearer ${SUPABASE_SERVICE_KEY}` } }
    );
    if (!resp.ok) return res.status(200).json({ valid: false, error: 'License server error' });

    const rows = await resp.json();
    if (!rows || rows.length === 0) {
      return res.status(200).json({ valid: false, error: 'Invalid license key' });
    }

    const lic = rows[0];
    const now = new Date();
    const expires = new Date(lic.expires_at);
    const valid = lic.status === 'active' && now <= expires;

    return res.status(200).json({
      valid,
      tier: lic.tier,
      status: lic.status,
      expires_at: lic.expires_at,
      source: 'database',
    });
  } catch (err) {
    console.error('Validate error:', err);
    return res.status(500).json({ error: err.message });
  }
};
