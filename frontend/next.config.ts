import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const apiBase = process.env.API_PROXY_BASE ?? "http://127.0.0.1:8003";
    return [
      {
        // Django exige le slash final (APPEND_SLASH) ; Next le supprime avant de
        // matcher la règle. On le réajoute ici, côté destination, pour que Django
        // resolve sans renvoyer un 301 qui ferait boucler Next et lui-même.
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*/`,
      },
    ];
  },
};

export default nextConfig;
