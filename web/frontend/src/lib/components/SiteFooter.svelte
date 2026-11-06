<script lang="ts">
  import { t } from '#lib/i18n.js';
</script>

<footer class="site-footer" data-testid="site-footer">
  <p>
    <span class="label">{$t('footer.bug')}</span>
    <a href="https://github.com/AnonShield/anonshield/issues" target="_blank" rel="noopener">{$t('footer.issue')}</a>
    <span>{$t('footer.or_write')}</span>
    <a href="mailto:contact@anonshield.org" data-testid="footer-contact">contact@anonshield.org</a>
  </p>
  <p>
    <span class="label">{$t('footer.security')}</span>
    <a href="mailto:security@anonshield.org" data-testid="footer-security">security@anonshield.org</a>
  </p>
</footer>

<style>
  .site-footer {
    border-top: 1px solid var(--color-border);
    padding: var(--space-6) var(--space-8);
    display: flex; flex-wrap: wrap; justify-content: center;
    gap: var(--space-2) var(--space-8);
    font-size: var(--text-sm);
    color: var(--color-text-secondary);
  }
  .site-footer p {
    margin: 0;
    display: flex; flex-wrap: wrap; justify-content: center; align-items: baseline;
    gap: 0 0.4em;
    text-align: center;
  }
  .label { color: var(--color-text-primary); font-weight: 600; }
  .site-footer a { color: var(--color-accent); text-decoration: none; }
  .site-footer a:hover, .site-footer a:focus-visible { text-decoration: underline; }
  @media (max-width: 640px) {
    .site-footer { padding: var(--space-5) var(--space-4); }
  }
</style>
