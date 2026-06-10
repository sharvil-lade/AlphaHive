"use client";

import React, { useState, useEffect } from "react";
import type { TechnicalPostureResponse, SentimentResponse } from "../types/generated";
import {
  fetchQuote,
  fetchProfile,
  fetchHistory,
  fetchTechnicalPosture,
  fetchSentiment,
  runAgentWorkflow,
  fetchReportsHistory,
  fetchReportDetail,
  getDownloadUrl,
  addPortfolioHolding,
  updatePortfolioHolding,
  deletePortfolioHolding,
  fetchPortfolioSummary,
  fetchWatchlist,
  addToWatchlist,
  deleteFromWatchlist,
  fetchAlerts,
  createAlert,
  deleteAlert,
  runAlertCheck,
  runBacktest
} from "../services/api";
import { useAgentStream } from "../hooks/useAgentStream";
import {
  TrendingUp,
  Search,
  Cpu,
  BarChart3,
  ListTodo,
  TrendingDown,
  Layers,
  Activity,
  CheckCircle2,
  HelpCircle,
  FileText,
  AlertTriangle,
  Play,
  RotateCcw,
  BookOpen
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar
} from "recharts";

// Simulated real-world stock history for charts
const HISTORICAL_DATA: Record<string, any[]> = {
  NVDA: [
    { date: "May 18", price: 905.3, volume: 45000000, rsi: 45 },
    { date: "May 19", price: 912.8, volume: 48000000, rsi: 48 },
    { date: "May 20", price: 924.5, volume: 52000000, rsi: 52 },
    { date: "May 21", price: 948.2, volume: 61000000, rsi: 59 },
    { date: "May 22", price: 963.5, volume: 55000000, rsi: 63 },
    { date: "May 23", price: 955.1, volume: 49000000, rsi: 58 },
    { date: "May 24", price: 978.8, volume: 59000000, rsi: 65 },
  ],
  TSLA: [
    { date: "May 18", price: 172.5, volume: 88000000, rsi: 38 },
    { date: "May 19", price: 174.2, volume: 82000000, rsi: 40 },
    { date: "May 20", price: 177.8, volume: 91000000, rsi: 45 },
    { date: "May 21", price: 173.1, volume: 95000000, rsi: 41 },
    { date: "May 22", price: 169.5, volume: 10200000, rsi: 34 },
    { date: "May 23", price: 165.2, volume: 11000000, rsi: 29 },
    { date: "May 24", price: 168.4, volume: 98000000, rsi: 35 },
  ]
};

// Fallback Mock data for Technical Posture evaluation
const MOCK_TA_POSTURE: Record<string, any> = {
  NVDA: {
    symbol: "NVDA",
    close: 978.80,
    score: 85,
    rating: "BUY",
    summary: "Technical indicators suggest robust bullish momentum for NVDA. Moving averages trend is supportive.",
    signals: {
      rsi: { score: 15, signal: "accumulating_bullish" },
      macd: { score: 20, signal: "bullish_crossover" },
      trends: { score: 30, signal: "strong_bullish_trend" },
      bollinger: { score: 15, signal: "overextended_bullish" },
      volume: { score: 10, signal: "high_volume_accumulation" }
    },
    pivots: {
      pivot: 960.50,
      r1: 985.00,
      s1: 945.00,
      r2: 1010.00,
      s2: 920.00
    }
  },
  TSLA: {
    symbol: "TSLA",
    close: 168.40,
    score: -45,
    rating: "SELL",
    summary: "Technical indicators indicate severe bearish momentum or overextension for TSLA. Exercise caution.",
    signals: {
      rsi: { score: -15, signal: "overbought_bearish" },
      macd: { score: -20, signal: "bearish_crossover" },
      trends: { score: -20, signal: "strong_bearish_trend" },
      bollinger: { score: -15, signal: "overextended_bearish" },
      volume: { score: -10, signal: "high_volume_distribution" }
    },
    pivots: {
      pivot: 172.10,
      r1: 178.55,
      s1: 164.30,
      r2: 185.20,
      s2: 157.60
    }
  }
};

// Fallback Mock data for Sentiment Posture evaluation
const MOCK_SENTIMENT_POSTURE: Record<string, any> = {
  NVDA: {
    symbol: "NVDA",
    score: 82,
    rating: "BUY",
    summary: "Sentiment around NVIDIA remains extremely positive, powered by strong Blackwell launch prospects and increased hyperscaler CapEx allocation. Social channels demonstrate intense call-buying momentum.",
    opportunities: [
      "Intense customer demand for Blackwell B200 platforms",
      "Increasing hyperscaler capital expenditure budgets",
      "Dominant moat around CUDA software library integration"
    ],
    threats: [
      "TSMC packaging capacity constraints (CoWoS packaging bottlenecks)",
      "Export restrictions in key international markets"
    ],
    source: "local_lexical_fallback"
  },
  TSLA: {
    symbol: "TSLA",
    score: -35,
    rating: "SELL",
    summary: "Tesla sentiment is moderately bearish, weighed down by compressed automotive profit margins and global price wars. Social channels indicate heightened caution over short-term deliveries.",
    opportunities: [
      "Potential margin acceleration from future compact car platforms",
      "Utility energy storage business growing over 20%"
    ],
    threats: [
      "Sustained price reductions compressing automotive margins below 16%",
      "Robotaxi autonomous timeline risks pushing back monetization"
    ],
    source: "local_lexical_fallback"
  }
};

// Simulated Multi-Agent Execution Steps
const AGENT_SIMULATION_STEPS = [
  { agent: "Research Agent", msg: "Scanning Finnhub metrics and basic fundamentals...", duration: 800 },
  { agent: "Research Agent", msg: "Extracted: P/E Ratio: 78.4, Market Cap: $2.4T, Beta: 1.85", duration: 800 },
  { agent: "Technical Agent", msg: "Analyzing RSI, MACD, and Bollinger Bands...", duration: 900 },
  { agent: "Technical Agent", msg: "MACD crossover is bullish. RSI oversold on 4H chart.", duration: 800 },
  { agent: "News Agent", msg: "Polling company headlines from Finnhub & Reddit...", duration: 1000 },
  { agent: "News Agent", msg: "Evaluated 18 recent articles: Sentiment is +82% Positive.", duration: 800 },
  { agent: "Risk Agent", msg: "Checking downside drawdown parameters and sector risks...", duration: 900 },
  { agent: "Risk Agent", msg: "Risk profile: Moderate volatility, high growth support.", duration: 800 },
  { agent: "Decision Agent", msg: "Synthesizing individual reports and building consensus...", duration: 1000 },
  { agent: "Decision Agent", msg: "Memo compiled successfully. Final Verdict: BUY.", duration: 500 }
];

const renderMarkdown = (markdown: string) => {
  if (!markdown) return null;
  let html = markdown
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  html = html.replace(/^&gt;\s+(.*)$/gm, '<blockquote class="border-l-4 border-cyanGlow/50 pl-4 py-1 my-2 bg-cyanGlow/5 italic text-gray-300">$1</blockquote>');
  html = html.replace(/^#\s+(.*)$/gm, '<h1 class="text-xl font-black text-white mt-6 mb-3 border-b border-terminal-border pb-2">$1</h1>');
  html = html.replace(/^##\s+(.*)$/gm, '<h2 class="text-base font-bold text-cyanGlow mt-5 mb-2">$1</h2>');
  html = html.replace(/^###\s+(.*)$/gm, '<h3 class="text-sm font-semibold text-gray-200 mt-4 mb-2">$1</h3>');
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-extrabold">$1</strong>');
  html = html.replace(/^\*\s+(.*)$/gm, '<li class="list-disc list-inside ml-4 my-1 text-gray-300">$1</li>');
  html = html.replace(/^-\s+(.*)$/gm, '<li class="list-disc list-inside ml-4 my-1 text-gray-300">$1</li>');
  html = html.replace(/^---$/gm, '<hr class="border-terminal-border my-6" />');

  const paragraphs = html.split('\n');
  const processed = paragraphs.map(p => {
    p = p.trim();
    if (!p) return '';
    if (p.startsWith('<h') || p.startsWith('<li') || p.startsWith('<hr') || p.startsWith('<blockquote') || p.startsWith('</blockquote')) {
      return p;
    }
    return `<p class="my-2 text-gray-300">${p}</p>`;
  });

  return (
    <div 
      className="markdown-content space-y-2 text-xs leading-relaxed text-gray-300 font-sans"
      dangerouslySetInnerHTML={{ __html: processed.join('\n') }} 
    />
  );
};

export default function Dashboard() {
  const [ticker, setTicker] = useState("NVDA");
  const [searchQuery, setSearchQuery] = useState("Should I buy Nvidia stock right now?");
  const [currentTab, setCurrentTab] = useState("research");
  
  // Technical Analysis Posture State
  const [taPosture, setTaPosture] = useState<TechnicalPostureResponse | null>(null);
  
  // Sentiment Analysis Posture State
  const [sentimentPosture, setSentimentPosture] = useState<SentimentResponse | null>(null);
  
  // Agent Execution State
  const [isRunning, setIsRunning] = useState(false);
  const [agentLogs, setAgentLogs] = useState<any[]>([]);
  const [showMemo, setShowMemo] = useState(true);

  // Session & History state
  const [sessionId, setSessionId] = useState<string>("");
  const [reportsHistory, setReportsHistory] = useState<any[]>([]);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [memoReport, setMemoReport] = useState<any>(null);

  // Health Telemetry
  const [telemetry, setTelemetry] = useState({
    postgres: "connected",
    redis: "cached",
    qdrant: "synced"
  });

  // Simulated live prices
  const [livePrice, setLivePrice] = useState(978.80);
  const [priceChange, setPriceChange] = useState(23.70);
  const [percentChange, setPercentChange] = useState(2.48);

  const [chartData, setChartData] = useState<any[]>([]);

  // Portfolio States
  const [portfolioSummary, setPortfolioSummary] = useState<any>(null);
  const [isAddingHolding, setIsAddingHolding] = useState(false);
  const [newHoldingSymbol, setNewHoldingSymbol] = useState("");
  const [newHoldingShares, setNewHoldingShares] = useState("");
  const [newHoldingPrice, setNewHoldingPrice] = useState("");
  const [editingHoldingId, setEditingHoldingId] = useState<string | null>(null);
  const [editHoldingShares, setEditHoldingShares] = useState("");
  const [editHoldingPrice, setEditHoldingPrice] = useState("");

  // Watchlist & Alerts States
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [triggeredAlertsLog, setTriggeredAlertsLog] = useState<any[]>([]);
  const [newWatchlistSymbol, setNewWatchlistSymbol] = useState("");
  const [newAlertSymbol, setNewAlertSymbol] = useState("");
  const [newAlertTriggerType, setNewAlertTriggerType] = useState("price_above");
  const [newAlertTriggerValue, setNewAlertTriggerValue] = useState("");
  const [alertsActiveOnly, setAlertsActiveOnly] = useState(true);

  // Backtesting States
  const [backtestSymbol, setBacktestSymbol] = useState("NVDA");
  const [backtestStrategy, setBacktestStrategy] = useState("rsi");
  const [backtestRange, setBacktestRange] = useState("1y");
  const [backtestCapital, setBacktestCapital] = useState("10000");
  const [backtestResult, setBacktestResult] = useState<any | null>(null);
  const [isBacktestingLoading, setIsBacktestingLoading] = useState(false);
  const [backtestError, setBacktestError] = useState<string | null>(null);

  const handleRunBacktest = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!backtestSymbol) return;
    setIsBacktestingLoading(true);
    setBacktestError(null);
    try {
      const res = await runBacktest(
        backtestSymbol.toUpperCase().trim(),
        backtestStrategy,
        parseFloat(backtestCapital) || 10000.0,
        backtestRange
      );
      setBacktestResult(res);
    } catch (err: any) {
      console.error("Failed to run backtest:", err);
      setBacktestError(err.message || "Failed to execute backtest. Please try again.");
    } finally {
      setIsBacktestingLoading(false);
    }
  };

  useEffect(() => {
    if (currentTab === "backtest") {
      if (ticker && backtestSymbol !== ticker) {
        setBacktestSymbol(ticker);
      }
    }
  }, [currentTab, ticker]);

  const loadWatchlistAndAlerts = async () => {
    if (!sessionId) return;
    try {
      const wl = await fetchWatchlist(sessionId);
      setWatchlist(wl);
      const al = await fetchAlerts(sessionId, alertsActiveOnly);
      setAlerts(al);
    } catch (e) {
      console.error("Failed to load watchlist/alerts:", e);
    }
  };

  useEffect(() => {
    if (sessionId) {
      loadWatchlistAndAlerts();
    }
  }, [sessionId, alertsActiveOnly]);

  const loadPortfolio = async () => {
    if (!sessionId) return;
    try {
      const summary = await fetchPortfolioSummary(sessionId);
      setPortfolioSummary(summary);
    } catch (e) {
      console.error("Failed to load portfolio summary:", e);
    }
  };

  useEffect(() => {
    if (currentTab === "portfolio") {
      loadPortfolio();
    }
  }, [currentTab, sessionId]);

  const handleAddHolding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHoldingSymbol || !newHoldingShares || !newHoldingPrice || !sessionId) return;
    try {
      await addPortfolioHolding(
        sessionId,
        newHoldingSymbol.toUpperCase().trim(),
        parseFloat(newHoldingShares),
        parseFloat(newHoldingPrice)
      );
      setNewHoldingSymbol("");
      setNewHoldingShares("");
      setNewHoldingPrice("");
      setIsAddingHolding(false);
      loadPortfolio();
    } catch (err) {
      console.error("Failed to add position:", err);
    }
  };

  const handleUpdateHolding = async (holdingId: string) => {
    if (!editHoldingShares || !editHoldingPrice) return;
    try {
      await updatePortfolioHolding(
        holdingId,
        parseFloat(editHoldingShares),
        parseFloat(editHoldingPrice)
      );
      setEditingHoldingId(null);
      loadPortfolio();
    } catch (err) {
      console.error("Failed to update position:", err);
    }
  };

  const handleDeleteHolding = async (holdingId: string) => {
    if (!confirm("Are you sure you want to delete this position?")) return;
    try {
      await deletePortfolioHolding(holdingId);
      loadPortfolio();
    } catch (err) {
      console.error("Failed to delete position:", err);
    }
  };

  const handleAddToWatchlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWatchlistSymbol || !sessionId) return;
    try {
      await addToWatchlist(sessionId, newWatchlistSymbol.toUpperCase().trim());
      setNewWatchlistSymbol("");
      loadWatchlistAndAlerts();
    } catch (e) {
      console.error("Failed to add to watchlist:", e);
    }
  };

  const handleRemoveFromWatchlist = async (symbol: string) => {
    if (!sessionId) return;
    try {
      await deleteFromWatchlist(sessionId, symbol);
      loadWatchlistAndAlerts();
    } catch (e) {
      console.error("Failed to delete from watchlist:", e);
    }
  };

  const handleCreateAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAlertSymbol || !newAlertTriggerType || !newAlertTriggerValue || !sessionId) return;
    try {
      await createAlert(
        sessionId,
        newAlertSymbol.toUpperCase().trim(),
        newAlertTriggerType,
        parseFloat(newAlertTriggerValue)
      );
      setNewAlertSymbol("");
      setNewAlertTriggerValue("");
      loadWatchlistAndAlerts();
    } catch (e) {
      console.error("Failed to create alert:", e);
    }
  };

  const handleDeleteAlert = async (alertId: string) => {
    if (!sessionId) return;
    try {
      await deleteAlert(sessionId, alertId);
      loadWatchlistAndAlerts();
    } catch (e) {
      console.error("Failed to delete alert:", e);
    }
  };

  const handleTriggerAlertCheck = async () => {
    try {
      const triggered = await runAlertCheck();
      if (triggered && triggered.length > 0) {
        setTriggeredAlertsLog((prev) => [...triggered, ...prev]);
      }
      loadWatchlistAndAlerts();
    } catch (e) {
      console.error("Failed to execute alert checks:", e);
    }
  };

  // Initialize session ID
  useEffect(() => {
    let sid = localStorage.getItem("session_id");
    if (!sid) {
      sid = "session_" + Math.random().toString(36).substring(2, 15);
      localStorage.setItem("session_id", sid);
    }
    setSessionId(sid);
  }, []);

  // Fetch history when sessionId is set
  useEffect(() => {
    if (!sessionId) return;
    const loadHistory = async () => {
      try {
        const history = await fetchReportsHistory(sessionId);
        setReportsHistory(history);
      } catch (e) {
        console.error("Failed to load reports history:", e);
      }
    };
    loadHistory();
  }, [sessionId]);

  // Load report detail
  const loadCompletedReport = async (runId: string) => {
    try {
      const detail = await fetchReportDetail(runId);
      setMemoReport(detail);
      
      // Update active ticker to match the report's ticker
      if (detail.ticker && detail.ticker !== ticker) {
        setTicker(detail.ticker);
      }
      setShowMemo(true);
    } catch (e) {
      console.error("Failed to load report detail:", e);
    }
  };

  // Log streaming hook
  useAgentStream(
    currentRunId,
    (log) => {
      setAgentLogs((prev) => {
        const exists = prev.some((l) => l.agent === log.node && l.msg === log.message);
        if (exists) return prev;
        return [
          ...prev,
          {
            agent: log.node,
            msg: log.message,
            timestamp: new Date(log.timestamp).toLocaleTimeString(),
            id: prev.length,
          },
        ];
      });
    },
    async (doneMsg) => {
      setIsRunning(false);
      if (currentRunId) {
        await loadCompletedReport(currentRunId);
        // Refresh history list
        if (sessionId) {
          const history = await fetchReportsHistory(sessionId);
          setReportsHistory(history);
        }
      }
      setCurrentRunId(null);
    },
    (err) => {
      console.error("Agent run streaming failed:", err);
      setIsRunning(false);
      setCurrentRunId(null);
    }
  );

  // Active runner trigger
  const runAgentWorkflowTrigger = async () => {
    setIsRunning(true);
    setAgentLogs([]);
    setShowMemo(false);
    setMemoReport(null);
    
    // Parse ticker from searchQuery or use active state
    let symbol = ticker;
    const match = searchQuery.match(/\b([A-Za-z]{2,5})\b/);
    if (match) {
      const candidate = match[1].toUpperCase();
      if (["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL", "META"].includes(candidate)) {
        symbol = candidate;
        setTicker(candidate);
      }
    }
    
    try {
      const run = await runAgentWorkflow(symbol, sessionId);
      setCurrentRunId(run.id);
    } catch (e) {
      console.error("Failed to start agent run:", e);
      setIsRunning(false);
    }
  };

  useEffect(() => {
    // Default static mock data first
    setChartData(HISTORICAL_DATA[ticker] || HISTORICAL_DATA.NVDA);
    setTaPosture(MOCK_TA_POSTURE[ticker] || MOCK_TA_POSTURE.NVDA);
    setSentimentPosture(MOCK_SENTIMENT_POSTURE[ticker] || MOCK_SENTIMENT_POSTURE.NVDA);

    const fetchLiveData = async () => {
      try {
        // 1. Fetch Quote
        const quote = await fetchQuote(ticker);
        setLivePrice(quote.price);
        setPriceChange(quote.change);
        setPercentChange(quote.percent_change);

        // Fetch Technical Posture
        const taData = await fetchTechnicalPosture(ticker);
        setTaPosture(taData);

        // Fetch Sentiment Posture
        const sentimentData = await fetchSentiment(ticker);
        setSentimentPosture(sentimentData);

        // 2. Fetch History
        const history = await fetchHistory(ticker);
        if (history && history.length > 0) {
          // Format dates for chart X-axis
          const formatted = history.map((item: any) => {
            const parts = item.date.split("-");
            const dateObj = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            const shortDate = dateObj.toLocaleDateString("en-US", { month: "short", day: "numeric" });
            return {
              date: shortDate,
              price: item.close,
              volume: item.volume
            };
          });
          setChartData(formatted);
        }
      } catch (err) {
        // Fallback silently to static mock data on error (offline mode)
        console.warn("Backend API not reachable, running in offline demo mode:", err);
        setChartData(HISTORICAL_DATA[ticker] || HISTORICAL_DATA.NVDA);
        setTaPosture(MOCK_TA_POSTURE[ticker] || MOCK_TA_POSTURE.NVDA);
        setSentimentPosture(MOCK_SENTIMENT_POSTURE[ticker] || MOCK_SENTIMENT_POSTURE.NVDA);
      }
    };

    fetchLiveData();
  }, [ticker]);

  // Live Telemetry check
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/health");
        if (res.ok) {
          const data = await res.json();
          setTelemetry({
            postgres: data.services?.database === "healthy" ? "connected" : "error",
            redis: data.services?.redis === "healthy" ? "cached" : "error",
            qdrant: data.services?.qdrant === "healthy" ? "synced" : "error"
          });
        }
      } catch (e) {
        console.warn("Failed to fetch server health telemetry:", e);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const currentChartData = chartData;

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* 1. Left Glassmorphic Sidebar */}
      <aside className="w-64 border-r border-terminal-border bg-terminal-dark flex flex-col justify-between hidden md:flex">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyanGlow to-bullish flex items-center justify-center shadow-glow">
              <Cpu className="w-4 h-4 text-background" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                ANTIGRAVITY
              </h1>
              <span className="text-[10px] text-cyanGlow flex items-center gap-1 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-bullish animate-pulse"></span>
                AGENTIC LIVE
              </span>
            </div>
          </div>

          <nav className="space-y-1">
            {[
              { id: "research", label: "Analyst Workspace", icon: BarChart3 },
              { id: "agents", label: "Multi-Agent Arena", icon: Cpu },
              { id: "portfolio", label: "AI Portfolio", icon: Layers },
              { id: "alerts", label: "Watchlist & Alerts", icon: ListTodo },
              { id: "backtest", label: "Historical Backtest", icon: TrendingUp }
            ].map(item => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentTab(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-semibold transition-all ${
                    currentTab === item.id
                      ? "bg-cyanGlow/10 text-cyanGlow border-l-2 border-cyanGlow"
                      : "text-mutedText hover:bg-terminal-hover hover:text-white"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>
          {/* Recent Reports history list */}
          <div className="mt-6 border-t border-terminal-border pt-4 overflow-y-auto max-h-[220px]">
            <div className="text-[10px] font-bold text-mutedText uppercase tracking-wider mb-2">
              Recent Reports
            </div>
            <div className="space-y-1">
              {reportsHistory.length === 0 ? (
                <div className="text-[10px] text-mutedText italic p-2">No reports run in session</div>
              ) : (
                reportsHistory.map((report) => (
                  <button
                    key={report.run_id}
                    onClick={() => loadCompletedReport(report.run_id)}
                    className="w-full text-left px-2 py-1.5 rounded text-[10px] font-mono hover:bg-terminal-hover text-gray-300 hover:text-cyanGlow transition-all flex justify-between items-center"
                  >
                    <span>{report.ticker} ({report.recommendation.toUpperCase()})</span>
                    <span className="text-mutedText text-[8px]">
                      {new Date(report.created_at).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        {/* System telemetry levels at bottom of sidebar */}
        <div className="p-6 border-t border-terminal-border space-y-3">
          <div className="text-[10px] font-bold text-mutedText uppercase tracking-wider">
            System Telemetry
          </div>
          <div className="space-y-2 text-[11px]">
            <div className="flex justify-between items-center">
              <span className="text-mutedText">PostgreSQL</span>
              <span className="text-bullish flex items-center gap-1 font-semibold">
                <CheckCircle2 className="w-3 h-3" /> {telemetry.postgres}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-mutedText">Redis Cache</span>
              <span className="text-bullish flex items-center gap-1 font-semibold">
                <CheckCircle2 className="w-3 h-3" /> {telemetry.redis}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-mutedText">Qdrant DB</span>
              <span className="text-bullish flex items-center gap-1 font-semibold">
                <CheckCircle2 className="w-3 h-3" /> {telemetry.qdrant}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* 2. Main Dashboard Panel */}
      <div className="flex-1 flex flex-col overflow-hidden bg-background">
        {/* Top Header Bar */}
        <header className="h-16 border-b border-terminal-border px-6 flex items-center justify-between gap-4">
          {/* Perplexity-style Omnisearch */}
          <div className="flex-1 max-w-2xl relative">
            <Search className="w-4 h-4 text-mutedText absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Ask the AI Hedge Fund (e.g. 'Analyze Apple's current technical posture and SEC risk profile')"
              className="w-full h-10 pl-11 pr-24 rounded-lg bg-terminal-dark border border-terminal-border text-xs focus:outline-none focus:border-cyanGlow focus:ring-1 focus:ring-cyanGlow transition-all"
            />
            <button
              onClick={runAgentWorkflowTrigger}
              disabled={isRunning}
              className="absolute right-1 top-1 h-8 px-4 rounded bg-cyanGlow hover:bg-cyanGlow/90 text-background text-xs font-bold flex items-center gap-1 transition-all disabled:opacity-50"
            >
              <Cpu className="w-3.5 h-3.5" /> Analyze
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setTicker(t => t === "NVDA" ? "TSLA" : "NVDA")}
              className="px-3 py-1.5 border border-terminal-border rounded-lg bg-terminal-dark text-xs font-bold hover:bg-terminal-hover transition-all flex items-center gap-1"
            >
              Active Ticker: <span className="text-cyanGlow font-black">{ticker}</span>
            </button>
          </div>
        </header>

        {/* Page Inner Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {currentTab === "research" || currentTab === "agents" ? (
            <>
              {/* Indices Bar */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {[
              { index: "SPY (S&P 500)", val: "5,304.72", change: "+0.45%", isUp: true },
              { index: "QQQ (Nasdaq)", val: "18,802.10", change: "+0.82%", isUp: true },
              { index: ticker, val: `$${livePrice.toFixed(2)}`, change: `${priceChange >= 0 ? "+" : ""}${priceChange.toFixed(2)} (${percentChange >= 0 ? "+" : ""}${percentChange.toFixed(2)}%)`, isUp: priceChange >= 0 }
            ].map((idx, i) => (
              <div key={i} className="glass-panel p-4 rounded-xl flex justify-between items-center">
                <div>
                  <div className="text-[10px] text-mutedText font-semibold tracking-wider">{idx.index}</div>
                  <div className="text-sm font-bold mt-1">{idx.val}</div>
                </div>
                <span className={`text-xs font-bold flex items-center gap-0.5 px-2 py-0.5 rounded ${
                  idx.isUp ? "text-bullish bg-bullish/10" : "text-bearish bg-bearish/10"
                }`}>
                  {idx.isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  {idx.change}
                </span>
              </div>
            ))}

            <div className="glass-panel p-4 rounded-xl flex items-center justify-between">
              <div>
                <div className="text-[10px] text-mutedText font-semibold tracking-wider">TA posture</div>
                <div className={`text-sm font-black mt-1 ${
                  (taPosture?.rating || "HOLD") === "BUY" 
                    ? "text-bullish" 
                    : (taPosture?.rating || "HOLD") === "SELL" 
                      ? "text-bearish" 
                      : "text-yellow-500"
                }`}>
                  {(taPosture?.rating || "HOLD") === "BUY" 
                    ? "Bullish" 
                    : (taPosture?.rating || "HOLD") === "SELL" 
                      ? "Bearish" 
                      : "Neutral"}{" "}
                  ({taPosture?.score && taPosture.score >= 0 ? "+" : ""}{taPosture?.score ?? 0})
                </div>
              </div>
              <Activity className={`w-4 h-4 animate-pulse ${
                (taPosture?.rating || "HOLD") === "BUY" 
                  ? "text-bullish" 
                  : (taPosture?.rating || "HOLD") === "SELL" 
                    ? "text-bearish" 
                    : "text-yellow-500"
              }`} />
            </div>

            {/* Sentiment Posture Card */}
            <div className="glass-panel p-4 rounded-xl flex items-center justify-between">
              <div>
                <div className="text-[10px] text-mutedText font-semibold tracking-wider">Sentiment posture</div>
                <div className={`text-sm font-black mt-1 ${
                  (sentimentPosture?.rating || "HOLD") === "BUY" 
                    ? "text-bullish" 
                    : (sentimentPosture?.rating || "HOLD") === "SELL" 
                      ? "text-bearish" 
                      : "text-yellow-500"
                }`}>
                  {(sentimentPosture?.rating || "HOLD") === "BUY" 
                    ? "Bullish" 
                    : (sentimentPosture?.rating || "HOLD") === "SELL" 
                      ? "Bearish" 
                      : "Neutral"}{" "}
                  ({sentimentPosture?.score && sentimentPosture.score >= 0 ? "+" : ""}{sentimentPosture?.score ?? 0})
                </div>
              </div>
              <Cpu className={`w-4 h-4 animate-pulse ${
                (sentimentPosture?.rating || "HOLD") === "BUY" 
                  ? "text-bullish" 
                  : (sentimentPosture?.rating || "HOLD") === "SELL" 
                    ? "text-bearish" 
                    : "text-yellow-500"
              }`} />
            </div>
          </div>

          {/* Interactive Chart + Agent Log Drawer Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chart Area */}
            <div className="glass-panel p-6 rounded-2xl lg:col-span-2 flex flex-col justify-between min-h-[350px]">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h3 className="text-xs font-black text-mutedText uppercase tracking-wider">Historical Price Momentum</h3>
                  <div className="text-xl font-bold mt-1 flex items-baseline gap-2">
                    ${livePrice.toFixed(2)}
                    <span className={`text-xs font-semibold ${priceChange >= 0 ? "text-bullish" : "text-bearish"}`}>
                      {priceChange >= 0 ? "+" : ""}{priceChange.toFixed(2)} ({percentChange >= 0 ? "+" : ""}{percentChange.toFixed(2)}%)
                    </span>
                  </div>
                </div>

                <div className="flex gap-2">
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-cyanGlow/10 text-cyanGlow border border-cyanGlow/20">Daily Chart</span>
                </div>
              </div>

              {/* Area Chart visualization */}
              <div className="h-60 w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={currentChartData}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.25}/>
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" stroke="#4b5563" fontSize={10} tickLine={false} />
                    <YAxis stroke="#4b5563" domain={["auto", "auto"]} fontSize={10} tickLine={false} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: "#0b0f19", borderColor: "rgba(255, 255, 255, 0.08)", fontSize: "11px" }}
                      labelStyle={{ fontWeight: "bold" }}
                    />
                    <Area type="monotone" dataKey="price" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Agent Live logs panel */}
            <div className="glass-panel p-6 rounded-2xl flex flex-col">
              <div className="flex items-center justify-between mb-4 border-b border-terminal-border pb-3">
                <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5">
                  <Cpu className="w-4 h-4 text-cyanGlow" /> Multi-Agent Logs
                </h3>
                {isRunning ? (
                  <span className="text-[10px] text-cyanGlow animate-pulse flex items-center gap-1 font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyanGlow animate-ping"></span>
                    Running Flow
                  </span>
                ) : (
                  <span className="text-[10px] text-mutedText font-semibold">Standby</span>
                )}
              </div>

              {/* Log List View */}
              <div className="flex-1 overflow-y-auto space-y-3 max-h-[260px] text-[11px] font-mono pr-2">
                {agentLogs.length === 0 ? (
                  <div className="h-full flex flex-col justify-center items-center text-mutedText py-12 text-center">
                    <Cpu className="w-8 h-8 text-terminal-border mb-2 animate-bounce" />
                    <span>No active agent runs.</span>
                    <button
                      onClick={runAgentWorkflowTrigger}
                      className="mt-3 px-3 py-1.5 rounded bg-cyanGlow/10 hover:bg-cyanGlow/20 text-cyanGlow text-[10px] font-bold border border-cyanGlow/20"
                    >
                      Trigger Demo Run
                    </button>
                  </div>
                ) : (
                  agentLogs.map((log) => (
                    <div key={log.id} className="p-2.5 rounded bg-terminal-dark border border-terminal-border flex flex-col gap-1 animate-slide-up">
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] font-bold text-cyanGlow uppercase">{log.agent}</span>
                        <span className="text-[9px] text-mutedText">{log.timestamp}</span>
                      </div>
                      <p className="text-gray-300">{log.msg}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Technical Analysis Engine details */}
          {taPosture && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-slide-up">
              {/* Column 1: Core Oscillators */}
              <div className="glass-panel p-5 rounded-2xl space-y-4">
                <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5 border-b border-terminal-border pb-2">
                  <Activity className="w-4 h-4 text-cyanGlow" /> Core Oscillators
                </h3>
                
                <div className="space-y-4">
                  {/* RSI */}
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-xs font-bold text-white">RSI (14)</div>
                      <div className="text-[10px] text-mutedText mt-0.5 uppercase">
                        Signal: {taPosture.signals?.rsi?.signal?.replace(/_/g, " ") || "neutral"}
                      </div>
                    </div>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      taPosture.signals?.rsi?.score > 0 
                        ? "text-bullish bg-bullish/10 border border-bullish/20" 
                        : taPosture.signals?.rsi?.score < 0 
                          ? "text-bearish bg-bearish/10 border border-bearish/20" 
                          : "text-gray-400 bg-gray-400/10 border border-gray-400/20"
                    }`}>
                      Score: {taPosture.signals?.rsi?.score ?? 0}
                    </span>
                  </div>

                  {/* MACD */}
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-xs font-bold text-white">MACD (12, 26, 9)</div>
                      <div className="text-[10px] text-mutedText mt-0.5 uppercase">
                        Signal: {taPosture.signals?.macd?.signal?.replace(/_/g, " ") || "neutral"}
                      </div>
                    </div>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      taPosture.signals?.macd?.score > 0 
                        ? "text-bullish bg-bullish/10 border border-bullish/20" 
                        : taPosture.signals?.macd?.score < 0 
                          ? "text-bearish bg-bearish/10 border border-bearish/20" 
                          : "text-gray-400 bg-gray-400/10 border border-gray-400/20"
                    }`}>
                      Score: {taPosture.signals?.macd?.score ?? 0}
                    </span>
                  </div>

                  {/* Bollinger Bands */}
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-xs font-bold text-white">Bollinger Bands (20, 2)</div>
                      <div className="text-[10px] text-mutedText mt-0.5 uppercase">
                        Signal: {taPosture.signals?.bollinger?.signal?.replace(/_/g, " ") || "neutral"}
                      </div>
                    </div>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      taPosture.signals?.bollinger?.score > 0 
                        ? "text-bullish bg-bullish/10 border border-bullish/20" 
                        : taPosture.signals?.bollinger?.score < 0 
                          ? "text-bearish bg-bearish/10 border border-bearish/20" 
                          : "text-gray-400 bg-gray-400/10 border border-gray-400/20"
                    }`}>
                      Score: {taPosture.signals?.bollinger?.score ?? 0}
                    </span>
                  </div>
                </div>
              </div>

              {/* Column 2: Moving Averages Trend */}
              <div className="glass-panel p-5 rounded-2xl space-y-4">
                <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5 border-b border-terminal-border pb-2">
                  <TrendingUp className="w-4 h-4 text-cyanGlow" /> Trend System
                </h3>
                
                <div className="space-y-4">
                  {/* Overall Trend Score */}
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="text-xs font-bold text-white">Consensus Trend</div>
                      <div className="text-[10px] text-mutedText mt-0.5 uppercase">
                        {taPosture.signals?.trends?.signal?.replace(/_/g, " ") || "neutral"}
                      </div>
                    </div>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      taPosture.signals?.trends?.score > 0 
                        ? "text-bullish bg-bullish/10 border border-bullish/20" 
                        : taPosture.signals?.trends?.score < 0 
                          ? "text-bearish bg-bearish/10 border border-bearish/20" 
                          : "text-gray-400 bg-gray-400/10 border border-gray-400/20"
                    }`}>
                      Score: {taPosture.signals?.trends?.score ?? 0}
                    </span>
                  </div>

                  {/* Volume Confirmation */}
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="text-xs font-bold text-white">Volume Confirmation</div>
                      <div className="text-[10px] text-mutedText mt-0.5 uppercase">
                        {taPosture.signals?.volume?.signal?.replace(/_/g, " ") || "neutral"}
                      </div>
                    </div>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      taPosture.signals?.volume?.score > 0 
                        ? "text-bullish bg-bullish/10 border border-bullish/20" 
                        : taPosture.signals?.volume?.score < 0 
                          ? "text-bearish bg-bearish/10 border border-bearish/20" 
                          : "text-gray-400 bg-gray-400/10 border border-gray-400/20"
                    }`}>
                      Score: {taPosture.signals?.volume?.score ?? 0}
                    </span>
                  </div>
                </div>
              </div>

              {/* Column 3: Pivot Point Support & Resistance */}
              <div className="glass-panel p-5 rounded-2xl space-y-4">
                <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5 border-b border-terminal-border pb-2">
                  <BarChart3 className="w-4 h-4 text-cyanGlow" /> Pivot Boundaries (Classic)
                </h3>
                
                {taPosture.pivots ? (
                  <div className="grid grid-cols-5 gap-2 text-center text-[10px] font-mono">
                    <div className="p-1.5 bg-bearish/5 border border-bearish/20 rounded">
                      <span className="text-bearish font-black block">R2</span>
                      <span className="text-gray-300 font-bold mt-1 block">${taPosture.pivots.r2.toFixed(2)}</span>
                    </div>
                    <div className="p-1.5 bg-bearish/5 border border-bearish/20 rounded">
                      <span className="text-bearish/80 block">R1</span>
                      <span className="text-gray-200 mt-1 block">${taPosture.pivots.r1.toFixed(2)}</span>
                    </div>
                    <div className="p-1.5 bg-cyanGlow/5 border border-cyanGlow/25 rounded">
                      <span className="text-cyanGlow font-black block">P</span>
                      <span className="text-white font-bold mt-1 block">${taPosture.pivots.pivot.toFixed(2)}</span>
                    </div>
                    <div className="p-1.5 bg-bullish/5 border border-bullish/20 rounded">
                      <span className="text-bullish/80 block">S1</span>
                      <span className="text-gray-200 mt-1 block">${taPosture.pivots.s1.toFixed(2)}</span>
                    </div>
                    <div className="p-1.5 bg-bullish/5 border border-bullish/20 rounded">
                      <span className="text-bullish font-black block">S2</span>
                      <span className="text-gray-300 font-bold mt-1 block">${taPosture.pivots.s2.toFixed(2)}</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-mutedText text-center py-4">No pivots calculated</div>
                )}
                <div className="text-[10px] text-mutedText leading-relaxed">
                  Support and resistance bounds calculated based on previous daily high, low, and closing metrics.
                </div>
              </div>
            </div>
          )}

          {/* 3. Compiled Investment Report Memo */}
          {showMemo && (
            <div className="glass-panel p-6 rounded-2xl space-y-6 animate-slide-up">
              <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-terminal-border pb-4 gap-4">
                <div>
                  <span className="text-[10px] font-bold uppercase text-cyanGlow tracking-wider">Research Artifact</span>
                  <h2 className="text-lg font-black mt-0.5 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-cyanGlow" /> AI Investment Memo: {ticker}
                  </h2>
                </div>

                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-mutedText font-semibold">Recommendation:</span>
                    <span className={`text-xs font-black uppercase px-3 py-1 rounded ${
                      (memoReport?.report?.recommendation || sentimentPosture?.rating || "HOLD") === "BUY" 
                        ? "text-bullish bg-bullish/10 border border-bullish/20" 
                        : (memoReport?.report?.recommendation || sentimentPosture?.rating || "HOLD") === "SELL" 
                          ? "text-bearish bg-bearish/10 border border-bearish/20" 
                          : "text-yellow-500 bg-yellow-500/10 border border-yellow-500/20"
                    }`}>
                      {memoReport?.report?.recommendation || sentimentPosture?.rating || "HOLD"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-mutedText font-semibold">Confidence Score:</span>
                    <span className="text-sm font-black text-cyanGlow">
                      {memoReport?.report?.confidence_score !== undefined 
                        ? memoReport.report.confidence_score 
                        : (sentimentPosture?.score !== undefined ? Math.abs(sentimentPosture.score) : 50)}/100
                    </span>
                  </div>

                  {memoReport?.report && (
                    <div className="flex items-center gap-2">
                      <a
                        href={getDownloadUrl(memoReport.run_id, "pdf")}
                        download
                        className="px-3 py-1.5 border border-terminal-border rounded-lg bg-terminal-dark text-xs font-bold text-gray-300 hover:text-cyanGlow hover:bg-terminal-hover transition-all flex items-center gap-1.5"
                      >
                        <FileText className="w-3.5 h-3.5 text-cyanGlow" /> PDF Download
                      </a>
                      <a
                        href={getDownloadUrl(memoReport.run_id, "markdown")}
                        download
                        className="px-3 py-1.5 border border-terminal-border rounded-lg bg-terminal-dark text-xs font-bold text-gray-300 hover:text-cyanGlow hover:bg-terminal-hover transition-all flex items-center gap-1.5"
                      >
                        <BookOpen className="w-3.5 h-3.5 text-cyanGlow" /> MD Download
                      </a>
                    </div>
                  )}
                </div>
              </div>

              {/* Memo Core Content */}
              {memoReport?.report?.content_markdown ? (
                <div className="p-4 rounded-xl bg-terminal-dark border border-terminal-border overflow-x-auto">
                  {renderMarkdown(memoReport.report.content_markdown)}
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 text-xs leading-relaxed">
                  <div className="lg:col-span-2 space-y-4">
                    <div>
                      <h4 className="font-bold text-white mb-1.5 flex items-center gap-1.5">
                        <BookOpen className="w-3.5 h-3.5 text-cyanGlow" /> Executive Summary
                      </h4>
                      <p className="text-gray-300">
                        {sentimentPosture?.summary || "No sentiment summary loaded."}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-4 rounded-xl bg-bullish/5 border border-bullish/10">
                        <h5 className="font-bold text-bullish mb-2 flex items-center gap-1">
                          <TrendingUp className="w-3.5 h-3.5" /> Bullish Catalysts (Opportunities)
                        </h5>
                        <ul className="space-y-1.5 text-gray-300 list-disc list-inside">
                          {sentimentPosture?.opportunities?.map((opp: string, i: number) => (
                            <li key={i}>{opp}</li>
                          )) || <li>No opportunities identified.</li>}
                        </ul>
                      </div>

                      <div className="p-4 rounded-xl bg-bearish/5 border border-bearish/10">
                        <h5 className="font-bold text-bearish mb-2 flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5" /> Key Risks & Concerns (Threats)
                        </h5>
                        <ul className="space-y-1.5 text-gray-300 list-disc list-inside">
                          {sentimentPosture?.threats?.map((threat: string, i: number) => (
                            <li key={i}>{threat}</li>
                          )) || <li>No threats identified.</li>}
                        </ul>
                      </div>
                    </div>
                  </div>

                  {/* Quantitative breakdown side block */}
                  <div className="p-4 rounded-xl bg-terminal-dark border border-terminal-border space-y-4">
                    <h4 className="font-bold text-white mb-2 flex items-center gap-1.5">
                      <BarChart3 className="w-3.5 h-3.5 text-cyanGlow" /> Core Financial Ratios
                    </h4>

                    <div className="space-y-2.5 text-[11px] font-mono">
                      <div className="flex justify-between border-b border-terminal-border pb-1.5">
                        <span className="text-mutedText">P/E Ratio</span>
                        <span className="text-gray-200">{ticker === "NVDA" ? "78.4" : "55.2"}</span>
                      </div>
                      <div className="flex justify-between border-b border-terminal-border pb-1.5">
                        <span className="text-mutedText">Gross Margin</span>
                        <span className="text-gray-200">{ticker === "NVDA" ? "76.2%" : "17.4%"}</span>
                      </div>
                      <div className="flex justify-between border-b border-terminal-border pb-1.5">
                        <span className="text-mutedText">Beta (Volatility)</span>
                        <span className="text-gray-200">{ticker === "NVDA" ? "1.85" : "2.10"}</span>
                      </div>
                      <div className="flex justify-between border-b border-terminal-border pb-1.5">
                        <span className="text-mutedText">10-K Risk Count</span>
                        <span className="text-cyanGlow font-bold">14 citations</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
            </>
          ) : currentTab === "portfolio" ? (
            <div className="space-y-6">
              {/* Portfolio Summary Header Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                <div className="glass-panel p-4 rounded-xl">
                  <div className="text-[10px] text-mutedText font-semibold tracking-wider uppercase">Portfolio Value</div>
                  <div className="text-lg font-bold mt-1 text-white">
                    ${portfolioSummary?.total_value?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || "0.00"}
                  </div>
                </div>

                <div className="glass-panel p-4 rounded-xl">
                  <div className="text-[10px] text-mutedText font-semibold tracking-wider uppercase">Total Cost Basis</div>
                  <div className="text-lg font-bold mt-1 text-gray-300">
                    ${portfolioSummary?.total_cost?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || "0.00"}
                  </div>
                </div>

                <div className="glass-panel p-4 rounded-xl">
                  <div className="text-[10px] text-mutedText font-semibold tracking-wider uppercase">Unrealized Gain / Loss</div>
                  <div className={`text-lg font-bold mt-1 ${
                    (portfolioSummary?.gain_loss ?? 0) >= 0 ? "text-bullish" : "text-bearish"
                  }`}>
                    {portfolioSummary?.gain_loss >= 0 ? "+" : ""}
                    ${portfolioSummary?.gain_loss?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || "0.00"}
                    <span className="text-xs ml-1 font-semibold">
                      ({portfolioSummary?.gain_loss_percentage >= 0 ? "+" : ""}
                      {portfolioSummary?.gain_loss_percentage?.toFixed(2) || "0.00"}%)
                    </span>
                  </div>
                </div>

                <div className="glass-panel p-4 rounded-xl">
                  <div className="text-[10px] text-mutedText font-semibold tracking-wider uppercase">Weighted Beta</div>
                  <div className="text-lg font-bold mt-1 text-cyanGlow">
                    {portfolioSummary?.weighted_beta?.toFixed(2) || "1.00"}
                  </div>
                </div>

                <div className="glass-panel p-4 rounded-xl">
                  <div className="text-[10px] text-mutedText font-semibold tracking-wider uppercase">Annualized Volatility</div>
                  <div className="text-lg font-bold mt-1 text-cyanGlow">
                    {portfolioSummary?.weighted_volatility !== undefined 
                      ? `${(portfolioSummary.weighted_volatility * 100).toFixed(1)}%`
                      : "0.0%"}
                  </div>
                </div>
              </div>

              {/* Add position section */}
              {isAddingHolding && (
                <form onSubmit={handleAddHolding} className="glass-panel p-4 rounded-xl border border-cyanGlow/25 space-y-4 max-w-2xl animate-slide-up">
                  <h4 className="text-xs font-bold text-white uppercase flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-cyanGlow" /> Add Position
                  </h4>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="text-[10px] text-mutedText block mb-1">Symbol</label>
                      <input 
                        type="text" 
                        value={newHoldingSymbol} 
                        onChange={e => setNewHoldingSymbol(e.target.value.toUpperCase())}
                        placeholder="e.g. AAPL" 
                        className="w-full h-8 bg-terminal-dark border border-terminal-border rounded px-2 text-xs text-white uppercase focus:outline-none focus:border-cyanGlow"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-mutedText block mb-1">Shares</label>
                      <input 
                        type="number" 
                        step="any"
                        value={newHoldingShares} 
                        onChange={e => setNewHoldingShares(e.target.value)}
                        placeholder="e.g. 10" 
                        className="w-full h-8 bg-terminal-dark border border-terminal-border rounded px-2 text-xs text-white focus:outline-none focus:border-cyanGlow"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-mutedText block mb-1">Avg Cost ($)</label>
                      <input 
                        type="number" 
                        step="any"
                        value={newHoldingPrice} 
                        onChange={e => setNewHoldingPrice(e.target.value)}
                        placeholder="e.g. 175.50" 
                        className="w-full h-8 bg-terminal-dark border border-terminal-border rounded px-2 text-xs text-white focus:outline-none focus:border-cyanGlow"
                        required
                      />
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button 
                      type="button" 
                      onClick={() => setIsAddingHolding(false)}
                      className="px-3 py-1.5 bg-terminal-hover text-[11px] font-bold rounded text-gray-300 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button 
                      type="submit" 
                      className="px-3 py-1.5 bg-cyanGlow text-[11px] font-bold rounded text-background hover:bg-cyanGlow/90"
                    >
                      Add Position
                    </button>
                  </div>
                </form>
              )}

              {/* Main portfolio grid split */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* holdings list ledger */}
                <div className="glass-panel p-6 rounded-2xl lg:col-span-2 space-y-4 overflow-x-auto">
                  <div className="flex justify-between items-center border-b border-terminal-border pb-3">
                    <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5">
                      <BarChart3 className="w-4 h-4 text-cyanGlow" /> Holdings Ledger
                    </h3>
                    {!isAddingHolding && (
                      <button
                        onClick={() => setIsAddingHolding(true)}
                        className="px-2.5 py-1 rounded bg-cyanGlow text-background text-[10px] font-bold hover:bg-cyanGlow/90 transition-all"
                      >
                        + Add Position
                      </button>
                    )}
                  </div>

                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-terminal-border text-[10px] text-mutedText uppercase tracking-wider">
                        <th className="py-2 px-4">Symbol</th>
                        <th className="py-2 px-4">Sector</th>
                        <th className="py-2 px-4">Shares</th>
                        <th className="py-2 px-4">Avg Cost</th>
                        <th className="py-2 px-4">Spot Price</th>
                        <th className="py-2 px-4">Value</th>
                        <th className="py-2 px-4">Gain/Loss</th>
                        <th className="py-2 px-4">Risk Factors</th>
                        <th className="py-2 px-4">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(!portfolioSummary?.holdings || portfolioSummary.holdings.length === 0) ? (
                        <tr>
                          <td colSpan={9} className="text-center py-8 text-mutedText italic text-xs">
                            No holdings in portfolio. Click Add Position to start indexing your assets.
                          </td>
                        </tr>
                      ) : (
                        portfolioSummary.holdings.map((h: any) => {
                          const isEditing = editingHoldingId === h.id;
                          return (
                            <tr key={h.id} className="border-b border-terminal-border hover:bg-terminal-hover/20">
                              <td className="py-3 px-4 font-bold text-white font-mono">{h.symbol}</td>
                              <td className="py-3 px-4 text-gray-400 text-[10px]">{h.sector}</td>
                              <td className="py-3 px-4 font-mono">
                                {isEditing ? (
                                  <input 
                                    type="number" 
                                    step="any"
                                    value={editHoldingShares} 
                                    onChange={e => setEditHoldingShares(e.target.value)}
                                    className="w-16 bg-terminal-dark border border-terminal-border rounded px-1.5 py-0.5 text-xs text-white text-center focus:outline-none focus:border-cyanGlow"
                                  />
                                ) : h.shares}
                              </td>
                              <td className="py-3 px-4 font-mono">
                                {isEditing ? (
                                  <input 
                                    type="number" 
                                    step="any"
                                    value={editHoldingPrice} 
                                    onChange={e => setEditHoldingPrice(e.target.value)}
                                    className="w-20 bg-terminal-dark border border-terminal-border rounded px-1.5 py-0.5 text-xs text-white text-center focus:outline-none focus:border-cyanGlow"
                                  />
                                ) : `$${h.average_buy_price.toFixed(2)}`}
                              </td>
                              <td className="py-3 px-4 font-mono">${h.current_price.toFixed(2)}</td>
                              <td className="py-3 px-4 font-mono font-bold text-gray-200">${h.total_value.toFixed(2)}</td>
                              <td className={`py-3 px-4 font-mono font-bold ${h.gain_loss >= 0 ? "text-bullish" : "text-bearish"}`}>
                                {h.gain_loss >= 0 ? "+" : ""}{h.gain_loss.toFixed(2)} ({h.gain_loss_percentage.toFixed(1)}%)
                              </td>
                              <td className="py-3 px-4 text-[10px] text-gray-400 font-mono">
                                Beta: {h.beta.toFixed(2)} | Vol: {(h.volatility*100).toFixed(1)}%
                              </td>
                              <td className="py-3 px-4">
                                {isEditing ? (
                                  <div className="flex gap-2">
                                    <button 
                                      onClick={() => handleUpdateHolding(h.id)}
                                      className="px-2 py-0.5 bg-bullish text-background text-[10px] font-bold rounded hover:bg-bullish/90"
                                    >
                                      Save
                                    </button>
                                    <button 
                                      onClick={() => setEditingHoldingId(null)}
                                      className="px-2 py-0.5 bg-terminal-hover text-gray-300 text-[10px] font-bold rounded hover:text-white"
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                ) : (
                                  <div className="flex gap-2">
                                    <button 
                                      onClick={() => {
                                        setEditingHoldingId(h.id);
                                        setEditHoldingShares(h.shares.toString());
                                        setEditHoldingPrice(h.average_buy_price.toString());
                                      }}
                                      className="text-cyanGlow hover:underline text-[11px] font-bold"
                                    >
                                      Edit
                                    </button>
                                    <button 
                                      onClick={() => handleDeleteHolding(h.id)}
                                      className="text-bearish hover:underline text-[11px] font-bold"
                                    >
                                      Remove
                                    </button>
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Right col: Sector Allocations & risk assessment */}
                <div className="space-y-6">
                  {/* Sector allocations list/bar visualizer */}
                  <div className="glass-panel p-5 rounded-2xl space-y-4">
                    <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5 border-b border-terminal-border pb-2">
                      <Layers className="w-4.5 h-4.5 text-cyanGlow" /> Sector Allocations
                    </h3>
                    <div className="space-y-4">
                      {portfolioSummary?.sector_weights && Object.keys(portfolioSummary.sector_weights).length > 0 ? (
                        Object.entries(portfolioSummary.sector_weights).map(([sector, weight]: any) => (
                          <div key={sector} className="space-y-1.5">
                            <div className="flex justify-between text-[11px] font-mono text-gray-300">
                              <span>{sector}</span>
                              <span className="text-cyanGlow font-bold">{weight.toFixed(1)}%</span>
                            </div>
                            <div className="w-full bg-terminal-dark h-1.5 rounded-full overflow-hidden border border-terminal-border">
                              <div 
                                className="bg-gradient-to-r from-cyanGlow to-bullish h-full rounded-full"
                                style={{ width: `${weight}%` }}
                              ></div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-mutedText italic text-center py-6 text-xs">No assets in portfolio</div>
                      )}
                    </div>
                  </div>

                  {/* Risk gauge card */}
                  <div className="glass-panel p-5 rounded-2xl space-y-4">
                    <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5 border-b border-terminal-border pb-2">
                      <Activity className="w-4.5 h-4.5 text-cyanGlow" /> AI Risk Assessment
                    </h3>
                    <div className="space-y-3 text-xs leading-relaxed text-gray-300">
                      <div className="flex justify-between items-center font-mono">
                        <span className="text-mutedText">Weighted Beta</span>
                        <span className={`font-bold ${portfolioSummary?.weighted_beta > 1.2 ? "text-bearish" : "text-bullish"}`}>
                          {portfolioSummary?.weighted_beta?.toFixed(2) || "0.00"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center font-mono">
                        <span className="text-mutedText">Annual Volatility</span>
                        <span className="text-cyanGlow font-bold">
                          {portfolioSummary?.weighted_volatility !== undefined 
                            ? `${(portfolioSummary.weighted_volatility * 100).toFixed(1)}%`
                            : "0.0%"}
                        </span>
                      </div>
                      
                      <div className="p-3 bg-terminal-dark rounded-lg border border-terminal-border text-[11px]">
                        <span className="font-bold text-white block mb-1">Risk Summary:</span>
                        {portfolioSummary?.weighted_beta > 1.3 ? (
                          <span>The portfolio exhibits high systematic risk (aggressive stance). Highly sensitive to general index movements.</span>
                        ) : portfolioSummary?.weighted_beta > 0.8 ? (
                          <span>The portfolio exhibits moderate systematic risk (balanced stance). Aligns closely with market return indices.</span>
                        ) : (
                          <span>The portfolio is conservative with low systematic risk. Volatility is defensive against market corrections.</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : currentTab === "alerts" ? (
            <div className="space-y-6">
              {/* Alert Notifications banner for triggered items */}
              {triggeredAlertsLog.length > 0 && (
                <div className="glass-panel p-4 rounded-xl border border-bearish/30 bg-bearish/5 space-y-2 animate-slide-up">
                  <div className="flex justify-between items-center border-b border-bearish/25 pb-1">
                    <h4 className="text-xs font-bold text-bearish flex items-center gap-1.5 uppercase">
                      <AlertTriangle className="w-4 h-4" /> Real-time Alert Triggers
                    </h4>
                    <button 
                      onClick={() => setTriggeredAlertsLog([])}
                      className="text-[10px] text-mutedText hover:text-white font-semibold"
                    >
                      Clear Log
                    </button>
                  </div>
                  <div className="space-y-1.5 max-h-32 overflow-y-auto">
                    {triggeredAlertsLog.map((t, idx) => (
                      <div key={idx} className="text-[11px] font-mono flex justify-between text-gray-300">
                        <span>
                          Stock <span className="text-white font-bold">{t.symbol}</span> crossed alert parameter <span className="text-cyanGlow font-bold">{t.trigger_type}</span>: Spot was <span className="text-bearish font-black">${t.current_value.toFixed(2)}</span> (Trigger: {t.trigger_value.toFixed(2)})
                        </span>
                        <span className="text-mutedText text-[9px]">{new Date(t.triggered_at).toLocaleTimeString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Grid with 2 columns: Watchlist and Alerts */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Watchlist card (Col 1) */}
                <div className="glass-panel p-6 rounded-2xl space-y-4">
                  <div className="flex justify-between items-center border-b border-terminal-border pb-3">
                    <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5">
                      <ListTodo className="w-4 h-4 text-cyanGlow" /> Watchlist Tracking
                    </h3>
                  </div>

                  <form onSubmit={handleAddToWatchlist} className="flex gap-2">
                    <input 
                      type="text" 
                      value={newWatchlistSymbol}
                      onChange={e => setNewWatchlistSymbol(e.target.value.toUpperCase())}
                      placeholder="Enter Stock Symbol (e.g. AAPL)" 
                      className="flex-1 h-9 bg-terminal-dark border border-terminal-border rounded px-3 text-xs text-white uppercase focus:outline-none focus:border-cyanGlow"
                      required
                    />
                    <button 
                      type="submit"
                      className="px-3 h-9 bg-cyanGlow text-background text-xs font-bold rounded hover:bg-cyanGlow/90 transition-all"
                    >
                      Add
                    </button>
                  </form>

                  <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                    {watchlist.length === 0 ? (
                      <div className="text-mutedText italic text-center py-6 text-xs">No watchlisted assets</div>
                    ) : (
                      watchlist.map((item) => (
                        <div key={item.id} className="p-3 bg-terminal-dark border border-terminal-border rounded-xl flex justify-between items-center hover:border-cyanGlow/30 transition-all">
                          <button
                            onClick={() => {
                              setTicker(item.symbol);
                              setCurrentTab("research");
                            }}
                            className="text-xs font-bold text-white hover:text-cyanGlow transition-all font-mono"
                          >
                            {item.symbol}
                          </button>
                          <button 
                            onClick={() => handleRemoveFromWatchlist(item.symbol)}
                            className="text-bearish text-[11px] font-bold hover:underline"
                          >
                            Remove
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Alerts config card (Col 2 & 3) */}
                <div className="glass-panel p-6 rounded-2xl lg:col-span-2 space-y-6">
                  <div className="flex justify-between items-center border-b border-terminal-border pb-3">
                    <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5">
                      <Cpu className="w-4 h-4 text-cyanGlow" /> Alert Configurations
                    </h3>
                    <div className="flex gap-3">
                      <button
                        onClick={handleTriggerAlertCheck}
                        className="px-2.5 py-1 rounded bg-gradient-to-r from-cyanGlow to-bullish text-background text-[10px] font-bold hover:opacity-90 transition-all flex items-center gap-1"
                      >
                        <Play className="w-3 h-3 text-background fill-background" /> Run Scanner check
                      </button>
                      <button
                        onClick={() => setAlertsActiveOnly(a => !a)}
                        className="px-2.5 py-1 rounded bg-terminal-hover border border-terminal-border text-gray-300 text-[10px] font-bold hover:text-white transition-all"
                      >
                        {alertsActiveOnly ? "Show All" : "Show Active Only"}
                      </button>
                    </div>
                  </div>

                  {/* Create alert form */}
                  <form onSubmit={handleCreateAlert} className="p-4 rounded-xl bg-terminal-dark/50 border border-terminal-border space-y-3">
                    <h4 className="text-[11px] font-bold text-white uppercase">Declare New Watchlist Alert</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div>
                        <label className="text-[10px] text-mutedText block mb-1">Stock Ticker</label>
                        <select
                          value={newAlertSymbol}
                          onChange={e => setNewAlertSymbol(e.target.value)}
                          className="w-full h-8 bg-terminal-dark border border-terminal-border rounded px-2 text-xs text-white focus:outline-none focus:border-cyanGlow font-mono"
                          required
                        >
                          <option value="">Select Asset...</option>
                          {watchlist.map(w => (
                            <option key={w.id} value={w.symbol}>{w.symbol}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] text-mutedText block mb-1">Trigger condition</label>
                        <select
                          value={newAlertTriggerType}
                          onChange={e => setNewAlertTriggerType(e.target.value)}
                          className="w-full h-8 bg-terminal-dark border border-terminal-border rounded px-2 text-xs text-white focus:outline-none focus:border-cyanGlow"
                          required
                        >
                          <option value="price_above">Price Spot Above ($)</option>
                          <option value="price_below">Price Spot Below ($)</option>
                          <option value="rsi_above">Technical RSI Above</option>
                          <option value="rsi_below">Technical RSI Below</option>
                          <option value="sentiment_drop">Sentiment Score Below</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] text-mutedText block mb-1">Trigger Threshold</label>
                        <input 
                          type="number"
                          step="any"
                          value={newAlertTriggerValue}
                          onChange={e => setNewAlertTriggerValue(e.target.value)}
                          placeholder="e.g. 150.00 / 30 / 60"
                          className="w-full h-8 bg-terminal-dark border border-terminal-border rounded px-2 text-xs text-white focus:outline-none focus:border-cyanGlow font-mono"
                          required
                        />
                      </div>
                    </div>
                    <div className="flex justify-end">
                      <button 
                        type="submit"
                        className="px-3 py-1.5 bg-cyanGlow text-background text-[11px] font-bold rounded hover:bg-cyanGlow/90 transition-all"
                      >
                        Create Alert
                      </button>
                    </div>
                  </form>

                  {/* Configured alerts table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse font-mono">
                      <thead>
                        <tr className="border-b border-terminal-border text-[10px] text-mutedText uppercase tracking-wider font-sans">
                          <th className="py-2 px-4">Symbol</th>
                          <th className="py-2 px-4">Condition</th>
                          <th className="py-2 px-4">Trigger Bound</th>
                          <th className="py-2 px-4">Status</th>
                          <th className="py-2 px-4">Created At</th>
                          <th className="py-2 px-4">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {alerts.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="text-center py-8 text-mutedText italic text-xs font-sans">
                              No configured alerts found. Ensure stock items are watchlisted to configure alerts.
                            </td>
                          </tr>
                        ) : (
                          alerts.map((al) => (
                            <tr key={al.id} className="border-b border-terminal-border hover:bg-terminal-hover/20">
                              <td className="py-3 px-4 font-bold text-white">{al.symbol}</td>
                              <td className="py-3 px-4 text-cyanGlow">{al.trigger_type.replace(/_/g, " ")}</td>
                              <td className="py-3 px-4 font-bold text-gray-200">{al.trigger_value.toFixed(2)}</td>
                              <td className="py-3 px-4">
                                <span className={`text-[10px] px-2 py-0.5 rounded font-sans font-bold ${
                                  al.is_active 
                                    ? "text-bullish bg-bullish/10 border border-bullish/25" 
                                    : "text-mutedText bg-terminal-hover border border-terminal-border"
                                }`}>
                                  {al.is_active ? "Active" : "Triggered"}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-mutedText text-[10px]">
                                {new Date(al.created_at).toLocaleDateString()}
                              </td>
                              <td className="py-3 px-4 font-sans">
                                <button 
                                  onClick={() => handleDeleteAlert(al.id)}
                                  className="text-bearish hover:underline text-[11px] font-bold"
                                >
                                  Delete
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          ) : currentTab === "backtest" ? (
            <div className="space-y-6 animate-fade-in">
              <div className="glass-panel p-6 rounded-2xl space-y-4">
                <div className="border-b border-terminal-border pb-3">
                  <h2 className="text-sm font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5">
                    <TrendingUp className="w-4 h-4 text-cyanGlow" /> Historical Backtest Simulation
                  </h2>
                  <p className="text-xs text-mutedText mt-1">
                    Simulate quantitative strategies historically to evaluate returns, Sharpe ratios, drawdowns, and transaction logs compared to S&P 500.
                  </p>
                </div>

                <form onSubmit={handleRunBacktest} className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
                  <div>
                    <label className="text-[10px] text-mutedText block mb-1">Asset Ticker</label>
                    <input 
                      type="text"
                      value={backtestSymbol}
                      onChange={e => setBacktestSymbol(e.target.value.toUpperCase())}
                      placeholder="e.g. NVDA"
                      className="w-full h-9 bg-terminal-dark border border-terminal-border rounded px-3 text-xs text-white uppercase focus:outline-none focus:border-cyanGlow font-mono"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-mutedText block mb-1">Trading Strategy</label>
                    <select
                      value={backtestStrategy}
                      onChange={e => setBacktestStrategy(e.target.value)}
                      className="w-full h-9 bg-terminal-dark border border-terminal-border rounded px-3 text-xs text-white focus:outline-none focus:border-cyanGlow"
                      required
                    >
                      <option value="rsi">RSI Reversal (Oversold/Overbought)</option>
                      <option value="ema_crossover">EMA 9/21 Trend Crossover</option>
                      <option value="macd_crossover">MACD Signal Line Crossover</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-mutedText block mb-1">Time Range</label>
                    <select
                      value={backtestRange}
                      onChange={e => setBacktestRange(e.target.value)}
                      className="w-full h-9 bg-terminal-dark border border-terminal-border rounded px-3 text-xs text-white focus:outline-none focus:border-cyanGlow"
                      required
                    >
                      <option value="1mo">1 Month</option>
                      <option value="3mo">3 Months</option>
                      <option value="6mo">6 Months</option>
                      <option value="1y">1 Year</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-mutedText block mb-1">Initial Capital ($)</label>
                    <input 
                      type="number"
                      value={backtestCapital}
                      onChange={e => setBacktestCapital(e.target.value)}
                      className="w-full h-9 bg-terminal-dark border border-terminal-border rounded px-3 text-xs text-white focus:outline-none focus:border-cyanGlow font-mono"
                      required
                    />
                  </div>
                  <div>
                    <button
                      type="submit"
                      disabled={isBacktestingLoading}
                      className="w-full h-9 bg-cyanGlow text-background text-xs font-bold rounded hover:bg-cyanGlow/90 disabled:opacity-50 transition-all cursor-pointer"
                    >
                      {isBacktestingLoading ? "Simulating..." : "Run Backtest"}
                    </button>
                  </div>
                </form>
              </div>

              {isBacktestingLoading && (
                <div className="glass-panel p-12 rounded-2xl flex flex-col items-center justify-center space-y-4">
                  <div className="w-8 h-8 border-4 border-cyanGlow border-t-transparent rounded-full animate-spin"></div>
                  <div className="text-xs text-cyanGlow font-bold uppercase tracking-wider animate-pulse">
                    Running strategy backtest...
                  </div>
                  <div className="text-[10px] text-mutedText italic text-center">
                    Retrieving historical quotes, computing technical vectors, and mapping portfolio systematic transactions.
                  </div>
                </div>
              )}

              {backtestError && (
                <div className="glass-panel p-4 rounded-xl border border-bearish/30 bg-bearish/5">
                  <h4 className="text-xs font-bold text-bearish flex items-center gap-1.5 uppercase">
                    <AlertTriangle className="w-4 h-4" /> Backtest Failure
                  </h4>
                  <p className="text-[11px] text-gray-300 mt-1">{backtestError}</p>
                </div>
              )}

              {backtestResult && !isBacktestingLoading && (
                <div className="space-y-6">
                  {/* Metrics Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div className="glass-panel p-4 rounded-2xl space-y-1">
                      <span className="text-[9px] font-bold text-mutedText uppercase tracking-wider block">Total Return</span>
                      <span className={`text-xl font-mono font-black block ${backtestResult.total_return >= 0 ? "text-bullish" : "text-bearish"}`}>
                        {backtestResult.total_return >= 0 ? "+" : ""}{(backtestResult.total_return * 100).toFixed(2)}%
                      </span>
                      <span className="text-[9px] text-gray-400 font-mono block">
                        Final: ${backtestResult.final_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                      </span>
                    </div>

                    <div className="glass-panel p-4 rounded-2xl space-y-1">
                      <span className="text-[9px] font-bold text-mutedText uppercase tracking-wider block">S&P 500 Return</span>
                      <span className={`text-xl font-mono font-black block ${backtestResult.benchmark_return >= 0 ? "text-bullish" : "text-bearish"}`}>
                        {backtestResult.benchmark_return >= 0 ? "+" : ""}{(backtestResult.benchmark_return * 100).toFixed(2)}%
                      </span>
                      <span className="text-[9px] text-gray-400 block font-sans">SPY Buy & Hold</span>
                    </div>

                    <div className="glass-panel p-4 rounded-2xl space-y-1">
                      <span className="text-[9px] font-bold text-mutedText uppercase tracking-wider block">Sharpe Ratio</span>
                      <span className="text-xl font-mono font-black text-cyanGlow block">
                        {backtestResult.sharpe_ratio.toFixed(2)}
                      </span>
                      <span className="text-[9px] text-gray-400 block font-sans">Risk-Adjusted Return</span>
                    </div>

                    <div className="glass-panel p-4 rounded-2xl space-y-1">
                      <span className="text-[9px] font-bold text-mutedText uppercase tracking-wider block">Max Drawdown</span>
                      <span className="text-xl font-mono font-black text-bearish block">
                        {(backtestResult.max_drawdown * 100).toFixed(2)}%
                      </span>
                      <span className="text-[9px] text-gray-400 block font-sans">Peak-to-Trough Decline</span>
                    </div>

                    <div className="glass-panel p-4 rounded-2xl space-y-1">
                      <span className="text-[9px] font-bold text-mutedText uppercase tracking-wider block">Win Rate</span>
                      <span className="text-xl font-mono font-black text-white block">
                        {(backtestResult.win_rate * 100).toFixed(0)}%
                      </span>
                      <span className="text-[9px] text-gray-400 font-mono block">
                        {backtestResult.total_trades} trades completed
                      </span>
                    </div>
                  </div>

                  {/* Equity Curve Chart */}
                  <div className="glass-panel p-6 rounded-2xl space-y-4">
                    <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5">
                      <Activity className="w-4 h-4 text-cyanGlow" /> Equity Curve Comparison
                    </h3>
                    <div className="h-[320px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={backtestResult.equity_curve}>
                          <defs>
                            <linearGradient id="colorPortfolio" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#00f2fe" stopOpacity={0.2}/>
                              <stop offset="95%" stopColor="#00f2fe" stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id="colorBenchmark" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#9ca3af" stopOpacity={0.1}/>
                              <stop offset="95%" stopColor="#9ca3af" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <XAxis 
                            dataKey="date" 
                            stroke="#4b5563" 
                            fontSize={10} 
                            tickLine={false} 
                            axisLine={false}
                          />
                          <YAxis 
                            stroke="#4b5563" 
                            fontSize={10} 
                            tickLine={false} 
                            axisLine={false}
                            domain={['auto', 'auto']}
                            tickFormatter={val => `$${val.toLocaleString()}`}
                          />
                          <Tooltip 
                            contentStyle={{ backgroundColor: "#0b0f17", borderColor: "#1f2937", borderRadius: "12px" }}
                            labelStyle={{ color: "#9ca3af", fontSize: "11px", fontWeight: "bold", fontFamily: "monospace" }}
                            itemStyle={{ fontSize: "12px", fontFamily: "monospace" }}
                            formatter={(value: any, name: any) => [
                              `$${Number(value).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`, 
                              name === "portfolio_value" ? "Strategy Portfolio" : "S&P 500 Benchmark"
                            ]}
                          />
                          <Area 
                            name="portfolio_value"
                            type="monotone" 
                            dataKey="portfolio_value" 
                            stroke="#00f2fe" 
                            strokeWidth={2}
                            fillOpacity={1} 
                            fill="url(#colorPortfolio)" 
                          />
                          <Area 
                            name="benchmark_value"
                            type="monotone" 
                            dataKey="benchmark_value" 
                            stroke="#9ca3af" 
                            strokeWidth={1.5}
                            strokeDasharray="4 4"
                            fillOpacity={1} 
                            fill="url(#colorBenchmark)" 
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Transaction Log */}
                  <div className="glass-panel p-6 rounded-2xl space-y-4">
                    <h3 className="text-xs font-black text-mutedText uppercase tracking-wider flex items-center gap-1.5">
                      <BookOpen className="w-4 h-4 text-cyanGlow" /> Simulation Transaction Ledger
                    </h3>
                    <div className="overflow-x-auto max-h-[400px] overflow-y-auto pr-1">
                      <table className="w-full text-left text-xs border-collapse font-mono">
                        <thead>
                          <tr className="border-b border-terminal-border text-[10px] text-mutedText uppercase tracking-wider font-sans">
                            <th className="py-2 px-4">Date</th>
                            <th className="py-2 px-4">Type</th>
                            <th className="py-2 px-4">Close Price</th>
                            <th className="py-2 px-4">Shares</th>
                            <th className="py-2 px-4">Transaction Value</th>
                            <th className="py-2 px-4">Net Profit/Loss</th>
                            <th className="py-2 px-4">Cash Remaining</th>
                          </tr>
                        </thead>
                        <tbody>
                          {backtestResult.trades.length === 0 ? (
                            <tr>
                              <td colSpan={7} className="text-center py-8 text-mutedText italic text-xs font-sans">
                                No trades executed. Strategy parameters were not crossed during this timeframe.
                              </td>
                            </tr>
                          ) : (
                            backtestResult.trades.map((trade: any, idx: number) => (
                              <tr key={idx} className="border-b border-terminal-border hover:bg-terminal-hover/20">
                                <td className="py-3 px-4 text-mutedText">{trade.date}</td>
                                <td className="py-3 px-4">
                                  <span className={`text-[10px] px-2 py-0.5 rounded font-sans font-bold ${
                                    trade.type.startsWith("BUY") 
                                      ? "text-bullish bg-bullish/10 border border-bullish/25" 
                                      : "text-bearish bg-bearish/10 border border-bearish/25"
                                  }`}>
                                    {trade.type}
                                  </span>
                                </td>
                                <td className="py-3 px-4 font-bold text-white">${trade.price.toFixed(2)}</td>
                                <td className="py-3 px-4 text-gray-300">{trade.shares.toLocaleString()}</td>
                                <td className="py-3 px-4 text-gray-300">${trade.value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                                <td className={`py-3 px-4 font-bold ${
                                  trade.type.startsWith("BUY") 
                                    ? "text-mutedText" 
                                    : trade.profit_loss >= 0 
                                      ? "text-bullish" 
                                      : "text-bearish"
                                }`}>
                                  {trade.type.startsWith("BUY") 
                                    ? "-" 
                                    : `${trade.profit_loss >= 0 ? "+" : ""}$${trade.profit_loss.toFixed(2)} (${trade.profit_loss_pct >= 0 ? "+" : ""}${trade.profit_loss_pct.toFixed(2)}%)`
                                  }
                                </td>
                                <td className="py-3 px-4 text-gray-400">${trade.cash_remaining.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-mutedText italic text-center py-20">Work in Progress</div>
          )}
        </div>
      </div>
    </div>
  );
}
