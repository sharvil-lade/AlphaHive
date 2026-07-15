"use client";

import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Pencil, Upload, KeyRound, Loader2 } from "lucide-react";
import { useSessionId } from "../../hooks/useSessionId";
import {
  fetchPortfolioSummary,
  addPortfolioHolding,
  updatePortfolioHolding,
  deletePortfolioHolding,
  importGrowwPortfolio,
  importPortfolioFile,
} from "../../services/api";
import { Card, Button, Input, PageHeader, Delta } from "../../components/ui/primitives";

export default function PortfolioPage() {
  const sessionId = useSessionId();
  const queryClient = useQueryClient();
  const [isAdding, setIsAdding] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [shares, setShares] = useState("");
  const [price, setPrice] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editShares, setEditShares] = useState("");
  const [editPrice, setEditPrice] = useState("");

  const [showImport, setShowImport] = useState(false);
  const [growwToken, setGrowwToken] = useState("");
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: summary } = useQuery({
    queryKey: ["portfolio", sessionId],
    queryFn: () => fetchPortfolioSummary(sessionId),
    enabled: !!sessionId,
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["portfolio", sessionId] });

  const handleGrowwImport = async () => {
    if (!growwToken.trim()) return;
    setImporting(true);
    setImportMsg(null);
    try {
      const result = await importGrowwPortfolio(sessionId, growwToken.trim(), true);
      setImportMsg({ ok: true, text: result.message || "Imported from Groww." });
      setGrowwToken("");
      refresh();
    } catch (e: any) {
      setImportMsg({ ok: false, text: e.message || "Groww import failed." });
    } finally {
      setImporting(false);
    }
  };

  const handleFileImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportMsg(null);
    try {
      const result = await importPortfolioFile(sessionId, file, true);
      setImportMsg({ ok: true, text: result.message || "Imported from file." });
      refresh();
    } catch (err: any) {
      setImportMsg({ ok: false, text: err.message || "File import failed." });
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol || !shares || !price) return;
    await addPortfolioHolding(sessionId, symbol.toUpperCase().trim(), parseFloat(shares), parseFloat(price));
    setSymbol("");
    setShares("");
    setPrice("");
    setIsAdding(false);
    refresh();
  };

  const handleUpdate = async (holdingId: string) => {
    if (!editShares || !editPrice) return;
    await updatePortfolioHolding(holdingId, parseFloat(editShares), parseFloat(editPrice));
    setEditingId(null);
    refresh();
  };

  const handleDelete = async (holdingId: string) => {
    await deletePortfolioHolding(holdingId);
    refresh();
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader
        title="Portfolio"
        description="Optional — add your Groww holdings so the chat can research in the context of what you own"
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-5xl w-full mx-auto">
        {summary && summary.holdings.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card>
              <div className="text-[11px] text-mutedText mb-1">Total Value</div>
              <div className="text-lg font-semibold">₹{summary.total_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
            </Card>
            <Card>
              <div className="text-[11px] text-mutedText mb-1">Gain / Loss</div>
              <div className="text-lg font-semibold"><Delta value={summary.gain_loss_percentage} /></div>
            </Card>
            <Card>
              <div className="text-[11px] text-mutedText mb-1">Weighted Beta</div>
              <div className="text-lg font-semibold">{summary.weighted_beta.toFixed(2)}</div>
            </Card>
            <Card>
              <div className="text-[11px] text-mutedText mb-1">Volatility</div>
              <div className="text-lg font-semibold">{(summary.weighted_volatility * 100).toFixed(1)}%</div>
            </Card>
          </div>
        )}

        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-mutedText">Holdings</h2>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { setShowImport((v) => !v); setImportMsg(null); }}>
              <Upload className="w-3.5 h-3.5" /> Import from Groww
            </Button>
            <Button variant="outline" onClick={() => setIsAdding((v) => !v)}>
              <Plus className="w-3.5 h-3.5" /> Add position
            </Button>
          </div>
        </div>

        {showImport && (
          <Card className="space-y-4">
            <div>
              <div className="text-sm font-medium mb-1 flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5" /> Option 1 — Groww access token
              </div>
              <p className="text-[12px] text-mutedText mb-2">
                Generate a daily access token on Groww&apos;s{" "}
                <a href="https://groww.in/trade-api" target="_blank" rel="noreferrer" className="underline">Trading APIs page</a>{" "}
                (requires a Groww API subscription; tokens expire at 6 AM daily) and paste it here to sync your holdings.
              </p>
              <div className="flex flex-wrap gap-2 items-end">
                <Input
                  value={growwToken}
                  onChange={(e) => setGrowwToken(e.target.value)}
                  placeholder="Paste Groww access token"
                  className="flex-1 min-w-[220px]"
                  type="password"
                />
                <Button onClick={handleGrowwImport} disabled={importing || !growwToken.trim()}>
                  {importing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null} Sync
                </Button>
              </div>
            </div>

            <div className="border-t border-surface-border pt-4">
              <div className="text-sm font-medium mb-1 flex items-center gap-1.5">
                <Upload className="w-3.5 h-3.5" /> Option 2 — Upload a statement (no subscription)
              </div>
              <p className="text-[12px] text-mutedText mb-2">
                Export Holdings or P&amp;L from Groww&apos;s Reports section (CSV or Excel) and upload the file.
                Importing replaces your current holdings.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileImport}
                disabled={importing}
                className="block text-sm text-mutedText file:mr-3 file:rounded-md file:border file:border-surface-border file:bg-surface file:px-3 file:py-1.5 file:text-sm file:text-foreground hover:file:bg-surface-hover"
              />
            </div>

            {importMsg && (
              <div className={importMsg.ok ? "text-[12px] text-bullish" : "text-[12px] text-bearish"}>
                {importMsg.text}
              </div>
            )}
          </Card>
        )}

        {isAdding && (
          <Card>
            <form onSubmit={handleAdd} className="flex flex-wrap gap-2 items-end">
              <div>
                <label className="text-[11px] text-mutedText block mb-1">Symbol</label>
                <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="RELIANCE" />
              </div>
              <div>
                <label className="text-[11px] text-mutedText block mb-1">Shares</label>
                <Input value={shares} onChange={(e) => setShares(e.target.value)} type="number" placeholder="10" />
              </div>
              <div>
                <label className="text-[11px] text-mutedText block mb-1">Avg. Buy Price</label>
                <Input value={price} onChange={(e) => setPrice(e.target.value)} type="number" placeholder="1250.00" />
              </div>
              <Button type="submit">Add</Button>
            </form>
          </Card>
        )}

        <Card className="p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border text-[11px] text-mutedText">
                <th className="text-left px-4 py-2 font-medium">Symbol</th>
                <th className="text-right px-4 py-2 font-medium">Shares</th>
                <th className="text-right px-4 py-2 font-medium">Avg. Price</th>
                <th className="text-right px-4 py-2 font-medium">Current</th>
                <th className="text-right px-4 py-2 font-medium">Value</th>
                <th className="text-right px-4 py-2 font-medium">Gain/Loss</th>
                <th className="text-right px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {(summary?.holdings ?? []).map((h: any) => (
                <tr key={h.id} className="border-b border-surface-border last:border-0">
                  {editingId === h.id ? (
                    <td colSpan={7} className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium w-20">{h.symbol}</span>
                        <Input value={editShares} onChange={(e) => setEditShares(e.target.value)} type="number" placeholder="Shares" className="w-24" />
                        <Input value={editPrice} onChange={(e) => setEditPrice(e.target.value)} type="number" placeholder="Avg price" className="w-28" />
                        <Button onClick={() => handleUpdate(h.id)}>Save</Button>
                        <Button variant="ghost" onClick={() => setEditingId(null)}>Cancel</Button>
                      </div>
                    </td>
                  ) : (
                    <>
                      <td className="px-4 py-2.5 font-medium">{h.symbol}</td>
                      <td className="px-4 py-2.5 text-right text-mutedText">{h.shares}</td>
                      <td className="px-4 py-2.5 text-right text-mutedText">{h.average_buy_price.toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right">{h.current_price.toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right">{h.total_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                      <td className="px-4 py-2.5 text-right"><Delta value={h.gain_loss_percentage} /></td>
                      <td className="px-4 py-2.5 text-right">
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={() => { setEditingId(h.id); setEditShares(String(h.shares)); setEditPrice(String(h.average_buy_price)); }}
                            className="p-1 text-mutedText hover:text-foreground"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => handleDelete(h.id)} className="p-1 text-mutedText hover:text-bearish">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
              {(!summary || summary.holdings.length === 0) && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-mutedText text-sm">
                    No holdings yet — import from Groww or add a position above. This is optional;
                    you can research any stock in chat without a portfolio.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
