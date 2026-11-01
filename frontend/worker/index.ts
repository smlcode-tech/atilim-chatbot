/**
 * Yayındaki `/api/*` isteklerini Render'daki API'ye iletir; diğer yolları Cloudflare statik
 * dosyalardan sunar (`wrangler.jsonc`, `run_worker_first`).
 *
 * Render da Cloudflare arkasında olduğu için bu istek bölgeler arası alt istektir ve Cloudflare
 * `CF-Connecting-IP`'yi Worker'ın sabit adresine çevirir. İstemci adresi bu yüzden kendi
 * başlığımızla (`X-Client-IP`) gider; API ona yalnızca `X-Proxy-Secret` doğruysa güvenir. İkisinin
 * de üzerine yazıldığı için istemcinin gönderdiği aynı adlı başlıklar geçmez.
 */
type Env = {
  API_ORIGIN: string
  PROXY_SECRET?: string
}

export default {
  async fetch(request, env): Promise<Response> {
    const url = new URL(request.url)
    const upstream = new Request(`${env.API_ORIGIN}${url.pathname}${url.search}`, request)
    upstream.headers.set('X-Proxy-Secret', env.PROXY_SECRET ?? '')
    upstream.headers.set('X-Client-IP', request.headers.get('CF-Connecting-IP') ?? '')
    try {
      return await fetch(upstream, { redirect: 'manual' })
    } catch {
      // Gövdesiz 502'yi arayüz "sunucuya ulaşılamıyor" diye gösterir (`api/client.ts`).
      return new Response(null, { status: 502 })
    }
  },
} satisfies ExportedHandler<Env>
