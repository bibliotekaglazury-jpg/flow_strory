import {defineConfig} from '@playwright/test';
export default defineConfig({timeout:90000,testDir:'./tests',testMatch:'**/*.spec.ts',use:{baseURL:process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3000',headless:true,channel:process.env.PLAYWRIGHT_CHANNEL || 'chrome'}, reporter:'list'});
