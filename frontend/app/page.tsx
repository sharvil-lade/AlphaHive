"use client";

import React, { useState, useEffect } from "react";
import type { TechnicalPostureResponse } from "../types/generated";
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

export default function Dashboard() {
  const [ticker, setTicker] = useState("NVDA");
  const [searchQuery, setSearchQuery] = useState("Should I buy Nvidia stock right now?");
  const [currentTab, setCurrentTab] = useState("research");
  
  // Technical Analysis Posture State
  const [taPosture, setTaPosture] = useState<TechnicalPostureResponse | null>(null);
  
  // Agent Execution State
  const [isRunning, setIsRunning] = useState(false);
  const [activeStep, setActiveStep] = useState<number>(-1);
  const [agentLogs, setAgentLogs] = useState<any[]>([]);
  const [showMemo, setShowMemo] = useState(true);

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

  useEffect(() => {
    // Default static mock data first
    setChartData(HISTORICAL_DATA[ticker] || HISTORICAL_DATA.NVDA);
    setTaPosture(MOCK_TA_POSTURE[ticker] || MOCK_TA_POSTURE.NVDA);

    const fetchLiveData = async () => {
      try {
        const host = "http://127.0.0.1:8000";
        
        // 1. Fetch Quote
        const quoteResp = await fetch(`${host}/api/v1/stocks/quote?symbol=${ticker}`);
        if (quoteResp.ok) {
          const quote = await quoteResp.json();
          setLivePrice(quote.price);
          setPriceChange(quote.change);
          setPercentChange(quote.percent_change);

          // Fetch Technical Posture
          const taResp = await fetch(`${host}/api/v1/indicators/ta?symbol=${ticker}`);
          if (taResp.ok) {
            const taData = await taResp.json();
            setTaPosture(taData);
          }
        }

        // 2. Fetch History
        const historyResp = await fetch(`${host}/api/v1/stocks/history?symbol=${ticker}`);
        if (historyResp.ok) {
          const history = await historyResp.json();
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
        setTaPosture(MOCK_TA_POSTURE[ticker] || MOCK_TA_POSTURE.NVDA);
      }
    };

    fetchLiveData();
  }, [ticker]);

  // Run Simulated Agent Sequence
  const runAgentSimulation = () => {
    setIsRunning(true);
    setActiveStep(0);
    setAgentLogs([]);
    setShowMemo(false);

    let stepIndex = 0;
    
    const executeStep = () => {
      if (stepIndex < AGENT_SIMULATION_STEPS.length) {
        const step = AGENT_SIMULATION_STEPS[stepIndex];
        setAgentLogs(prev => [
          ...prev, 
          {
            ...step,
            timestamp: new Date().toLocaleTimeString(),
            id: stepIndex
          }
        ]);
        setActiveStep(stepIndex);
        stepIndex++;
        setTimeout(executeStep, step.duration);
      } else {
        setIsRunning(false);
        setShowMemo(true);
      }
    };

    setTimeout(executeStep, 300);
  };

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
              { id: "alerts", label: "Watchlist & Alerts", icon: ListTodo }
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
              onClick={runAgentSimulation}
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
          {/* Indices Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                      onClick={runAgentSimulation}
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
                      ticker === "NVDA" ? "text-bullish bg-bullish/10 border border-bullish/20" : "text-bearish bg-bearish/10 border border-bearish/20"
                    }`}>
                      {ticker === "NVDA" ? "BUY" : "HOLD / SELL"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-mutedText font-semibold">Confidence Score:</span>
                    <span className="text-sm font-black text-cyanGlow">{ticker === "NVDA" ? "88/100" : "35/100"}</span>
                  </div>
                </div>
              </div>

              {/* Memo Core Content */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 text-xs leading-relaxed">
                <div className="lg:col-span-2 space-y-4">
                  <div>
                    <h4 className="font-bold text-white mb-1.5 flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5 text-cyanGlow" /> Executive Summary
                    </h4>
                    <p className="text-gray-300">
                      {ticker === "NVDA" ? (
                        "NVIDIA continues to demonstrate unparalleled market positioning in AI compute architecture. Recent channel checks indicate that customer demand for Hopper (H100/H200) remains intense, while backlog allocations for the upcoming Blackwell (B200) family extend well into late 2026. Financial metrics remain exceptionally robust, characterized by operating margins exceeding 60% and free cash flow yield scaling consistently."
                      ) : (
                        "Tesla experiences substantial near-term macro headwinds, including declining average transaction prices and compressed auto gross margins (ex-credits). While autonomous driving software (FSD v12) continues to advance, regulatory barriers and hardware rollouts suggest meaningful monetization is deferred. Maintain caution until volumes stabilize."
                      )}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl bg-bullish/5 border border-bullish/10">
                      <h5 className="font-bold text-bullish mb-2 flex items-center gap-1">
                        <TrendingUp className="w-3.5 h-3.5" /> Bullish Catalysts (Opportunities)
                      </h5>
                      <ul className="space-y-1.5 text-gray-300 list-disc list-inside">
                        {ticker === "NVDA" ? (
                          <>
                            <li>Blackwell platform launching ahead of schedule</li>
                            <li>Hyperscaler CapEx budgets increased by 22%</li>
                            <li>Sustained high barriers to entry in software SDK stack</li>
                          </>
                        ) : (
                          <>
                            <li>Next-generation $25k compact platform launch</li>
                            <li>Megapack utility storage margins scaling to 20%</li>
                            <li>Licensing potential for FSD capabilities</li>
                          </>
                        )}
                      </ul>
                    </div>

                    <div className="p-4 rounded-xl bg-bearish/5 border border-bearish/10">
                      <h5 className="font-bold text-bearish mb-2 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" /> Key Risks & Concerns (Threats)
                      </h5>
                      <ul className="space-y-1.5 text-gray-300 list-disc list-inside">
                        {ticker === "NVDA" ? (
                          <>
                            <li>Supply chain bottlenecks on CoWoS packaging</li>
                            <li>Increased regulatory export controls in Asian corridors</li>
                            <li>Potential digestion phase in hyperscaler hardware spending</li>
                          </>
                        ) : (
                          <>
                            <li>Sustained price wars in European/Chinese markets</li>
                            <li>Slower capital expenditure cycles by global consumers</li>
                            <li>Brand dilution and high execution beta</li>
                          </>
                        )}
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
