import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	PUBLIC_API_URL: {
		public: true,
		static: true,
		description: 'API base URL seen by the browser (inlined at build time).',
		// Unset: same origin, as behind the Caddy proxy (and the Vite dev proxy).
		schema: (value) => value || '/api'
	}
});
