import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// In Docker dev, BACKEND_URL=http://backend:8000; locally defaults to localhost.
const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
			},
			// Node server (`node build`), as run by the production image.
			adapter: adapter()
		})
	],
	server: {
		proxy: {
			'/api': {
				target: backendUrl,
				changeOrigin: true
			}
		}
	}
});
