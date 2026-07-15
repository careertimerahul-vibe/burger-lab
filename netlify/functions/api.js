// Netlify Function — proxies API calls to the Burger Lab POS backend
const API_URL = "http://srv1115160.hstgr.cloud:8901";
const API_KEY = "burgerlab_pos_2024";

export default async function handler(req) {
  const url = new URL(req.url);
  const path = url.pathname.replace("/.netlify/functions/api", "/api");
  const target = API_URL + path + (url.search || "");

  try {
    const resp = await fetch(target, {
      method: req.method,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${API_KEY}`,
      },
      body: req.method !== "GET" && req.method !== "HEAD" ? JSON.stringify(await req.json()) : undefined,
    });

    const data = await resp.json();
    return new Response(JSON.stringify(data), {
      status: resp.status,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
      },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: "Backend unavailable" }), {
      status: 502,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
    });
  }
}

export const config = { path: "/api/*" };
