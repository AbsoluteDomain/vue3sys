import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.example.mobileapp',
  appName: '产品管理系统',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
};

export default config;
