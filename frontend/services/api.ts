// next.config.js proxies /svc/api to FastAPI, so requests are same-origin and the
// httpOnly session cookie is sent automatically. Set NEXT_PUBLIC_API_URL only when the
// backend is on a different origin — then CORS_ORIGINS must list this one.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/svc/api';
const V1 = `${API_BASE_URL}/api/v1`;

/** Thrown for any non-2xx response, carrying the server's message and status. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly requestId?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${V1}${path}`, {
      credentials: 'same-origin',
      ...init,
      headers: {
        ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }

  if (!res.ok) {
    let detail = res.statusText || 'Request failed';
    let requestId: string | undefined;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : detail;
      requestId = body?.request_id;
    } catch {
      // Non-JSON error body (proxy timeout, HTML error page) — keep the status text.
    }
    throw new ApiError(detail, res.status, requestId);
  }

  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Session {
  authenticated: boolean;
  user_id?: string | null;
  email?: string | null;
  name?: string | null;
}

export interface Holding {
  id: string;
  symbol: string;
  shares: number;
  average_buy_price: number;
  current_price: number;
  total_value: number;
  total_cost: number;
  gain_loss: number;
  gain_loss_percentage: number;
  sector: string;
  beta: number;
  volatility: number;
}

export interface PortfolioSummary {
  portfolio_id: string;
  name: string;
  total_value: number;
  total_cost: number;
  gain_loss: number;
  gain_loss_percentage: number;
  weighted_beta: number;
  weighted_volatility: number;
  holdings: Holding[];
  sector_weights: Record<string, number>;
}

export interface ImportResult {
  imported: number;
  replaced: boolean;
  portfolio_id: string;
  message: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface TraceRecord {
  id: string;
  node: string;
  status: 'running' | 'completed' | 'failed';
  summary: string | null;
  label: string | null;
  rating: string | null;
  confidence: number | null;
}

export interface MessageRecord {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  traces: TraceRecord[];
}

export interface ConversationDetail extends Conversation {
  messages: MessageRecord[];
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const fetchSession = () => request<Session>('/auth/session');
export const signup = (email: string, password: string, name?: string) =>
  post<Session>('/auth/signup', { email, password, name });
export const login = (email: string, password: string) =>
  post<Session>('/auth/login', { email, password });
export const logout = () => post<void>('/auth/logout');
export const deleteAccount = () => request<void>('/auth/account', { method: 'DELETE' });
export const exportDataUrl = () => `${V1}/auth/export`;

// ── Portfolio ─────────────────────────────────────────────────────────────────

export const fetchPortfolioSummary = () => request<PortfolioSummary>('/portfolios/summary');

export const addPortfolioHolding = (symbol: string, shares: number, averageBuyPrice: number) =>
  post<Holding>('/portfolios/holdings', {
    symbol,
    shares,
    average_buy_price: averageBuyPrice,
  });

export const updatePortfolioHolding = (
  holdingId: string,
  shares: number,
  averageBuyPrice: number
) =>
  request<Holding>(`/portfolios/holdings/${holdingId}`, {
    method: 'PUT',
    body: JSON.stringify({ shares, average_buy_price: averageBuyPrice }),
  });

export const deletePortfolioHolding = (holdingId: string) =>
  request<void>(`/portfolios/holdings/${holdingId}`, { method: 'DELETE' });

export const importGrowwPortfolio = (accessToken: string, replace = true) =>
  post<ImportResult>('/portfolios/import/groww', { access_token: accessToken, replace });

export const importPortfolioFile = (file: File, replace = true) => {
  const form = new FormData();
  form.append('file', file);
  return request<ImportResult>(`/portfolios/import/file?replace=${replace}`, {
    method: 'POST',
    body: form,
  });
};

// ── Chat ──────────────────────────────────────────────────────────────────────

export const createConversation = (title?: string) =>
  post<Conversation>('/chat/conversations', { title });

export const fetchConversations = (limit = 50) =>
  request<Conversation[]>(`/chat/conversations?limit=${limit}`);

export const fetchConversationDetail = (conversationId: string) =>
  request<ConversationDetail>(`/chat/conversations/${conversationId}`);

export const renameConversation = (conversationId: string, title: string) =>
  request<Conversation>(`/chat/conversations/${conversationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });

export const deleteConversation = (conversationId: string) =>
  request<void>(`/chat/conversations/${conversationId}`, { method: 'DELETE' });

export const postChatMessage = (conversationId: string, content: string) =>
  post<{ user_message: MessageRecord; assistant_message: MessageRecord }>(
    `/chat/conversations/${conversationId}/messages`,
    { content }
  );

export const stopChatMessage = (messageId: string) =>
  post<{ status: string }>(`/chat/messages/${messageId}/stop`);

export const getChatStreamUrl = (messageId: string, fromIndex = 0) =>
  `${V1}/chat/messages/${messageId}/stream?from_index=${fromIndex}`;
