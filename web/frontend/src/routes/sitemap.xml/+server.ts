import type { RequestHandler } from './$types';

// Small static site: list the crawlable pages so search engines discover them
// quickly (linked from the homepage too, but a sitemap speeds up indexing).
export const prerender = true;

const BASE = 'https://anonshield.org';
const PAGES = ['/', '/slides', '/app'];

export const GET: RequestHandler = () => {
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${PAGES.map((p) => `  <url><loc>${BASE}${p}</loc><changefreq>monthly</changefreq></url>`).join('\n')}
</urlset>
`;
  return new Response(body, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 'max-age=0, s-maxage=3600',
    },
  });
};
