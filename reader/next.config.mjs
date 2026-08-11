/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [
      // The feed was a single stream before the split, served here. Readers
      // that subscribed then would otherwise stop updating without saying so.
      { source: "/feed.xml", destination: "/mixed/feed.xml", permanent: true },
    ];
  },
};

export default nextConfig;
