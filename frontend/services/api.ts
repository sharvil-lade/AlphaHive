const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchQuote(symbol: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stocks/quote?symbol=${symbol}`);
  if (!res.ok) throw new Error(`Failed to fetch quote: ${res.statusText}`);
  return res.json();
}

export async function fetchProfile(symbol: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stocks/profile?symbol=${symbol}`);
  if (!res.ok) throw new Error(`Failed to fetch profile: ${res.statusText}`);
  return res.json();
}

export async function fetchHistory(symbol: string, range: string = '1mo'): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stocks/history?symbol=${symbol}&range_str=${range}`);
  if (!res.ok) throw new Error(`Failed to fetch history: ${res.statusText}`);
  return res.json();
}

export async function fetchTechnicalPosture(symbol: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/indicators/ta?symbol=${symbol}`);
  if (!res.ok) throw new Error(`Failed to fetch technical posture: ${res.statusText}`);
  return res.json();
}

export async function fetchSentiment(symbol: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/sentiment/summary?symbol=${symbol}`);
  if (!res.ok) throw new Error(`Failed to fetch sentiment: ${res.statusText}`);
  return res.json();
}

export async function runAgentWorkflow(symbol: string, sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/agents/run?symbol=${symbol}&session_id=${sessionId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to trigger agent workflow: ${res.statusText}`);
  return res.json();
}

export async function fetchReportsHistory(sessionId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/reports/history?session_id=${sessionId}`);
  if (!res.ok) throw new Error(`Failed to fetch reports history: ${res.statusText}`);
  return res.json();
}

export async function fetchReportDetail(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/agents/run/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch report detail: ${res.statusText}`);
  return res.json();
}

export function getDownloadUrl(runId: string, format: 'markdown' | 'pdf'): string {
  return `${API_BASE_URL}/api/v1/reports/${runId}/${format}`;
}

export async function fetchPortfolio(sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/portfolios?session_id=${sessionId}`);
  if (!res.ok) throw new Error(`Failed to fetch portfolio: ${res.statusText}`);
  return res.json();
}

export async function addPortfolioHolding(
  sessionId: string,
  symbol: string,
  shares: number,
  averageBuyPrice: number
): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/portfolios/holdings?session_id=${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, shares, average_buy_price: averageBuyPrice }),
  });
  if (!res.ok) throw new Error(`Failed to add portfolio holding: ${res.statusText}`);
  return res.json();
}

export async function updatePortfolioHolding(
  holdingId: string,
  shares: number,
  averageBuyPrice: number
): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/portfolios/holdings/${holdingId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ shares, average_buy_price: averageBuyPrice }),
  });
  if (!res.ok) throw new Error(`Failed to update portfolio holding: ${res.statusText}`);
  return res.json();
}

export async function deletePortfolioHolding(holdingId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/portfolios/holdings/${holdingId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete portfolio holding: ${res.statusText}`);
}

export async function fetchPortfolioSummary(sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/portfolios/summary?session_id=${sessionId}`);
  if (!res.ok) throw new Error(`Failed to fetch portfolio summary: ${res.statusText}`);
  return res.json();
}

