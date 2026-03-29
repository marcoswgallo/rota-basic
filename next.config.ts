import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ["puppeteer-core", "@sparticuz/chromium", "sharp"],
  outputFileTracingIncludes: {
    "/api/cron": ["./public/fonts/**", "./public/*.png"],
  },
};

export default nextConfig;
