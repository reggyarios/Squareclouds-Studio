import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/", // Bolehkan Google merayapi Landing Page
      disallow: ["/admin-cms", "/login", "/api/"], // LARANG Google mengindeks halaman Admin/Login
    },
    sitemap: "https://squarecloudsmc.com/sitemap.xml",
  };
}
