const isDev = process.env.NODE_ENV === "development";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: false,
  // Dev only: proxy /api to the FastAPI backend (rewrites are ignored in static export builds)
  ...(isDev
    ? {
        async rewrites() {
          return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }];
        },
      }
    : {}),
};

export default nextConfig;
