import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    // shadcn primitives export their style variants and hooks next to the component, and the
    // router module declares its lazy pages beside the router: both are intentional, and
    // only cost a full reload instead of hot-swapping while editing.
    files: ['src/components/ui/**', 'src/routes/routes.tsx'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
])
