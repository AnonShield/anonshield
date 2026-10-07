import nodeAdapter from '@sveltejs/adapter-node';
import staticAdapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

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
			// ANON_STATIC_UI=1: plain files that the local image's backend serves
			// itself, with index.html as the fallback for every page.
			adapter: process.env.ANON_STATIC_UI ? staticAdapter({ fallback: 'index.html' }) : nodeAdapter()
		})
	],
	test: {
		// The logic modules (src/lib/*.ts); the screens are covered by web/e2e.
		include: ['src/**/*.test.ts']
	},
	server: {
		proxy: {
			'/api': {
				target: backendUrl,
				changeOrigin: true
			}
		}
	}
});
