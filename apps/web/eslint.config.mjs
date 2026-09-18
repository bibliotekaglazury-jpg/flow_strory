import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';
export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {settings: {next: {rootDir: 'apps/web/'}}, rules: {'@next/next/no-img-element': 'off'}},
  // Preserve upstream declarations and directives in generated audited source.
  // Application code, importer, tests and renderer wrappers retain their checks.
  {files: ['packages/video-templates/src/imported/**/*.tsx'], rules: {
    '@typescript-eslint/no-unused-vars': 'off',
    '@typescript-eslint/no-unused-expressions': 'off',
  }},
  globalIgnores(['**/.next/**', '**/next-env.d.ts', 'apps/web/public/vendor/**']),
]);
