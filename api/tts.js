import Groq from 'groq-sdk';

const client = new Groq({ apiKey: process.env.GROQ_API_KEY });

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { text, voice = 'autumn' } = req.body ?? {};

  if (!text || typeof text !== 'string') {
    return res.status(400).json({ error: 'text is required' });
  }

  const clean = text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/[📎◆◈🚀🐛👋🙌→•]/g, '')
    .replace(/<br>/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()
    .slice(0, 800);

  try {
    const response = await client.audio.speech.create({
      model: 'canopylabs/orpheus-v1-english',
      voice,
      response_format: 'wav',
      input: clean,
    });

    const buffer = Buffer.from(await response.arrayBuffer());
    res.setHeader('Content-Type', 'audio/wav');
    res.setHeader('Cache-Control', 'no-store');
    return res.send(buffer);
  } catch (err) {
    console.error('Groq TTS error:', err?.message);
    return res.status(502).json({ error: 'TTS generation failed', detail: err?.message });
  }
}
