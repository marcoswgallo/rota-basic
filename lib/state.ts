// lib/state.ts

interface ConvState {
  step: "date_ini" | "date_fim";
  base: string;
  dataIni?: string; // formato YYYY-MM-DD
  expires: number;  // timestamp ms
}

const states = new Map<string, ConvState>();

export function setConvState(
  chatId: string,
  state: Omit<ConvState, "expires">
): void {
  states.set(chatId, {
    ...state,
    expires: Date.now() + 10 * 60 * 1000,
  });
}

export function getConvState(chatId: string): ConvState | null {
  const s = states.get(chatId);
  if (!s) return null;
  if (Date.now() > s.expires) {
    states.delete(chatId);
    return null;
  }
  return s;
}

export function clearConvState(chatId: string): void {
  states.delete(chatId);
}
