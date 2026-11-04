import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['packages/**/*.test.ts', 'tests/contract/**/*.test.ts'],
    environment: 'node',
    passWithNoTests: false,
    allowOnly: false,
    maxWorkers: 2,
    testTimeout: 10000,
  },
});
