import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// In Docker dev, BACKEND_URL=http://backend:8000; locally defaults to localhost.
const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			'/api': {
				target: backendUrl,
				changeOrigin: true
			}
		}
	}
});
