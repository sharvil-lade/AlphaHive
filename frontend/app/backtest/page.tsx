"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Play } from "lucide-react";
import { runBacktest } from "../../services/api";
import { Card, Button, Input, Select, PageHeader, Delta } from "../../components/ui/primitives";

const STRATEGIES = [
  { value: "rsi", label: "RSI Mean Reversion" },
  { value: "ema_crossover", label: "EMA Crossover" },
  { value: "macd_crossover", label: "MACD Crossover" },
];

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("RELIANCE");
  const [strategy, setStrategy] = useState("rsi");
  const [range, setRange] = useState("1y");
  const [capital, setCapital] = useState("10000");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const isDark = mounted && resolvedTheme === "dark";
  const chartColors = {
    grid: isDark ? "#262626" : "#e4e4e7",
    tick: isDark ? "#a1a1a1" : "#71717a",
    line: isDark ? "#ededed" : "#0a0a0a",
    tooltipBg: isDark ? "#171717" : "#ffffff",
    tooltipBorder: isDark ? "#262626" : "#e4e4e7",
  };

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runBacktest(symbol.toUpperCase().trim(), strategy, parseFloat(capital) || 10000, range);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to run backtest.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader title="Backtest" description="Simulate a strategy against historical price data" />

      <div className="flex-1 overflow-y-auto p-6 max-w-5xl w-full mx-auto space-y-6">
        <Card>
          <form onSubmit={handleRun} className="flex flex-wrap gap-2 items-end">
            <div>
              <label className="text-[11px] text-mutedText block mb-1">Symbol</label>
              <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} />
            </div>
            <div>
              <label className="text-[11px] text-mutedText block mb-1">Strategy</label>
              <Select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                {STRATEGIES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </Select>
            </div>
            <div>
              <label className="text-[11px] text-mutedText block mb-1">Range</label>
              <Select value={range} onChange={(e) => setRange(e.target.value)}>
                <option value="3mo">3 months</option>
                <option value="6mo">6 months</option>
                <option value="1y">1 year</option>
              </Select>
            </div>
            <div>
              <label className="text-[11px] text-mutedText block mb-1">Initial Capital</label>
              <Input value={capital} onChange={(e) => setCapital(e.target.value)} type="number" />
            </div>
            <Button type="submit" disabled={loading}>
              <Play className="w-3.5 h-3.5" /> {loading ? "Running..." : "Run backtest"}
            </Button>
          </form>
          {error && <p className="text-bearish text-sm mt-3">{error}</p>}
        </Card>

        {result && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <Card>
                <div className="text-[11px] text-mutedText mb-1">Total Return</div>
                <div className="text-lg font-semibold"><Delta value={result.total_return * 100} /></div>
              </Card>
              <Card>
                <div className="text-[11px] text-mutedText mb-1">vs Benchmark</div>
                <div className="text-lg font-semibold"><Delta value={result.benchmark_return * 100} /></div>
              </Card>
              <Card>
                <div className="text-[11px] text-mutedText mb-1">Sharpe Ratio</div>
                <div className="text-lg font-semibold">{result.sharpe_ratio.toFixed(2)}</div>
              </Card>
              <Card>
                <div className="text-[11px] text-mutedText mb-1">Max Drawdown</div>
                <div className="text-lg font-semibold text-bearish">{(result.max_drawdown * 100).toFixed(1)}%</div>
              </Card>
            </div>

            <Card>
              <h2 className="text-sm font-medium text-mutedText mb-3">Equity Curve</h2>
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={result.equity_curve}>
                  <defs>
                    <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={chartColors.line} stopOpacity={0.25} />
                      <stop offset="100%" stopColor={chartColors.line} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: chartColors.tick }} minTickGap={40} />
                  <YAxis tick={{ fontSize: 11, fill: chartColors.tick }} width={60} />
                  <Tooltip
                    contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: 8, fontSize: 12 }}
                  />
                  <Area type="monotone" dataKey="portfolio_value" stroke={chartColors.line} fill="url(#portfolioGrad)" strokeWidth={1.5} name="Strategy" />
                  <Area type="monotone" dataKey="benchmark_value" stroke={chartColors.tick} fill="transparent" strokeWidth={1} strokeDasharray="4 4" name="Benchmark" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            <Card className="p-0 overflow-hidden">
              <h2 className="text-sm font-medium text-mutedText px-4 pt-4 pb-2">
                Trades ({result.total_trades}, {(result.win_rate * 100).toFixed(0)}% win rate)
              </h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-border text-[11px] text-mutedText">
                    <th className="text-left px-4 py-2 font-medium">Type</th>
                    <th className="text-left px-4 py-2 font-medium">Date</th>
                    <th className="text-right px-4 py-2 font-medium">Price</th>
                    <th className="text-right px-4 py-2 font-medium">P/L</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((t: any, i: number) => (
                    <tr key={i} className="border-b border-surface-border last:border-0">
                      <td className="px-4 py-2 capitalize">{t.type}</td>
                      <td className="px-4 py-2 text-mutedText">{t.date}</td>
                      <td className="px-4 py-2 text-right">{t.price.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right"><Delta value={t.profit_loss_pct * 100} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
