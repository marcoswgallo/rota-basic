import { runPipeline } from "@/lib/pipeline";

// Executa em segundo plano — até 800s
export const maxDuration = 300;

export async function GET(req: Request) {
  // Vercel injeta o header CRON_SECRET automaticamente
  const secret = req.headers.get("authorization");
  if (secret !== `Bearer ${process.env.CRON_SECRET}`) {
    return new Response("Unauthorized", { status: 401 });
  }

  console.log("[cron] Disparando pipeline agendado...");
  await runPipeline();

  return new Response("ok");
}
