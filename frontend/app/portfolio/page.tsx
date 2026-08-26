"use client";

import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Loader2, Pencil, Plus, Trash2, Upload } from "lucide-react";
import {
  addPortfolioHolding,
  deletePortfolioHolding,
  fetchPortfolioSummary,
  importGrowwPortfolio,
  importPortfolioFile,
  updatePortfolioHolding,
  ApiError,
} from "../../services/api";
import { useToast } from "../../components/ui/Toast";
import { Button, Card, Input, PageHeader, Delta } from "../../components/ui/primitives";

const currency = (n: number) => `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

export default function PortfolioPage() {
  const queryClient = useQueryClient();
  const toast = useToast();

  const [isAdding, setIsAdding] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [shares, setShares] = useState("");
  const [price, setPrice] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editShares, setEditShares] = useState("");
  const [editPrice, setEditPrice] = useState("");
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const [showImport, setShowImport] = useState(false);
  const [growwToken, setGrowwToken] = useState("");
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: summary, isLoading } = useQuery({
    queryKey: ["portfolio"],
    queryFn: fetchPortfolioSummary,
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["portfolio"] });

  const run = async (fn: () => Promise<unknown>, fallback: string) => {
    try {
      await fn();
      refresh();
      return true;
    } catch (e) {
      toast(e instanceof ApiError ? e.message : fallback, "error");
      return false;
    }
  };

  const handleGrowwImport = async () => {
    if (!growwToken.trim()) return;
    setImporting(true);
    try {
      const result = await importGrowwPortfolio(growwToken.trim(), true);
      toast(result.message || "Imported from Groww.");
      setGrowwToken("");
      refresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Groww import failed.", "error");
    } finally {
      setImporting(false);
    }
  };

  const handleFileImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await importPortfolioFile(file, true);
      toast(result.message || "Imported from file.");
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "File import failed.", "error");
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol || !shares || !price) return;
    const ok = await run(
      () => addPortfolioHolding(symbol.toUpperCase().trim(), parseFloat(shares), parseFloat(price)),
      "Couldn't add that holding."
    );
    if (ok) {
      setSymbol("");
      setShares("");
      setPrice("");
      setIsAdding(false);
      toast(`Added ${symbol.toUpperCase().trim()}.`);
    }
  };

  const handleUpdate = async (holdingId: string) => {
    if (!editShares || !editPrice) return;
    const ok = await run(
      () => updatePortfolioHolding(holdingId, parseFloat(editShares), parseFloat(editPrice)),
      "Couldn't update that holding."
    );
    if (ok) setEditingId(null);
  };

  const handleDelete = async (holdingId: string) => {
    const ok = await run(() => deletePortfolioHolding(holdingId), "Couldn't remove that holding.");
    if (ok) {
      setPendingDelete(null);
      toast("Holding removed.");
    }
  };

  const sectors = Object.entries(summary?.sector_weights ?? {}).sort((a, b) => b[1] - a[1]);
  const holdings = summary?.holdings ?? [];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader
        title="Portfolio"
        description="Optional — add your holdings so the chat can research in the context of what you own"
      />

      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 max-w-5xl w-full mx-auto">
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-[74px] rounded-lg border border-surface-border bg-surface animate-pulse" />
            ))}
          </div>
        ) : (
          holdings.length > 0 && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
                <Card>
                  <div className="text-[11px] text-mutedText mb-1">Total Value</div>
                  <div className="text-lg font-semibold">{currency(summary!.total_value)}</div>
                </Card>
                <Card>
                  <div className="text-[11px] text-mutedText mb-1">Gain / Loss</div>
                  <div className="text-lg font-semibold">
                    <Delta value={summary!.gain_loss_percentage} />
                  </div>
                </Card>
                <Card>
                  <div className="text-[11px] text-mutedText mb-1">Weighted Beta</div>
                  <div className="text-lg font-semibold">{summary!.weighted_beta.toFixed(2)}</div>
                </Card>
                <Card>
                  <div className="text-[11px] text-mutedText mb-1">Volatility</div>
                  <div className="text-lg font-semibold">{(summary!.weighted_volatility * 100).toFixed(1)}%</div>
                </Card>
              </div>

              {sectors.length > 0 && (
                <Card>
                  <h2 className="text-[11px] text-mutedText mb-3">Sector allocation</h2>
                  <ul className="space-y-2">
                    {sectors.map(([sector, weight]) => (
                      <li key={sector} className="flex items-center gap-3 text-[13px]">
                        <span className="w-28 sm:w-40 shrink-0 truncate text-mutedText">{sector}</span>
                        {/* A plain div bar beats pulling in a chart library for one metric. */}
                        <span className="flex-1 h-1.5 rounded-full bg-surface-hover overflow-hidden">
                          <span
                            className="block h-full bg-foreground/70 rounded-full"
                            style={{ width: `${Math.min(weight * 100, 100).toFixed(1)}%` }}
                          />
                        </span>
                        <span className="w-12 text-right tabular-nums">{(weight * 100).toFixed(1)}%</span>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </>
          )
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-medium text-mutedText">Holdings</h2>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setShowImport((v) => !v)}>
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
              <h3 className="text-sm font-medium mb-1 flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5" /> Option 1 — Groww access token
              </h3>
              <p className="text-[12px] text-mutedText mb-2">
                Generate a daily access token on Groww&apos;s{" "}
                <a href="https://groww.in/trade-api" target="_blank" rel="noreferrer" className="underline">
                  Trading APIs page
                </a>{" "}
                and paste it here. The token is used for this request only and never stored.
              </p>
              <div className="flex flex-wrap gap-2 items-end">
                <Input
                  value={growwToken}
                  onChange={(e) => setGrowwToken(e.target.value)}
                  placeholder="Paste Groww access token"
                  aria-label="Groww access token"
                  className="flex-1 min-w-[220px]"
                  type="password"
                />
                <Button onClick={handleGrowwImport} disabled={importing || !growwToken.trim()}>
                  {importing && <Loader2 className="w-3.5 h-3.5 animate-spin" />} Sync
                </Button>
              </div>
            </div>

            <div className="border-t border-surface-border pt-4">
              <h3 className="text-sm font-medium mb-1 flex items-center gap-1.5">
                <Upload className="w-3.5 h-3.5" /> Option 2 — Upload a statement (no subscription)
              </h3>
              <p className="text-[12px] text-mutedText mb-2">
                Export Holdings or P&amp;L from Groww&apos;s Reports section (CSV or Excel).
                Importing replaces your current holdings.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileImport}
                disabled={importing}
                aria-label="Upload holdings file"
                className="block w-full text-sm text-mutedText file:mr-3 file:rounded-md file:border file:border-surface-border file:bg-surface file:px-3 file:py-1.5 file:text-sm file:text-foreground hover:file:bg-surface-hover"
              />
            </div>
          </Card>
        )}

        {isAdding && (
          <Card>
            <form onSubmit={handleAdd} className="flex flex-wrap gap-2 items-end">
              <div>
                <label htmlFor="symbol" className="text-[11px] text-mutedText block mb-1">
                  Symbol
                </label>
                <Input id="symbol" required value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="RELIANCE" />
              </div>
              <div>
                <label htmlFor="shares" className="text-[11px] text-mutedText block mb-1">
                  Shares
                </label>
                <Input id="shares" required value={shares} onChange={(e) => setShares(e.target.value)} type="number" step="any" min="0" placeholder="10" />
              </div>
              <div>
                <label htmlFor="price" className="text-[11px] text-mutedText block mb-1">
                  Avg. Buy Price
                </label>
                <Input id="price" required value={price} onChange={(e) => setPrice(e.target.value)} type="number" step="any" min="0" placeholder="1250.00" />
              </div>
              <Button type="submit">Add</Button>
            </form>
          </Card>
        )}

        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[640px]">
              <caption className="sr-only">Your portfolio holdings</caption>
              <thead>
                <tr className="border-b border-surface-border text-[11px] text-mutedText">
                  <th scope="col" className="text-left px-4 py-2 font-medium">Symbol</th>
                  <th scope="col" className="text-right px-4 py-2 font-medium">Shares</th>
                  <th scope="col" className="text-right px-4 py-2 font-medium">Avg. Price</th>
                  <th scope="col" className="text-right px-4 py-2 font-medium">Current</th>
                  <th scope="col" className="text-right px-4 py-2 font-medium">Value</th>
                  <th scope="col" className="text-right px-4 py-2 font-medium">Gain/Loss</th>
                  <th scope="col" className="text-right px-4 py-2 font-medium">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr key={h.id} className="border-b border-surface-border last:border-0">
                    {editingId === h.id ? (
                      <td colSpan={7} className="px-4 py-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium w-20">{h.symbol}</span>
                          <Input value={editShares} onChange={(e) => setEditShares(e.target.value)} type="number" step="any" min="0" aria-label={`Shares of ${h.symbol}`} className="w-24" />
                          <Input value={editPrice} onChange={(e) => setEditPrice(e.target.value)} type="number" step="any" min="0" aria-label={`Average price of ${h.symbol}`} className="w-28" />
                          <Button onClick={() => handleUpdate(h.id)}>Save</Button>
                          <Button variant="ghost" onClick={() => setEditingId(null)}>Cancel</Button>
                        </div>
                      </td>
                    ) : (
                      <>
                        <th scope="row" className="px-4 py-2.5 font-medium text-left">{h.symbol}</th>
                        <td className="px-4 py-2.5 text-right text-mutedText tabular-nums">{h.shares}</td>
                        <td className="px-4 py-2.5 text-right text-mutedText tabular-nums">{h.average_buy_price.toFixed(2)}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums">{h.current_price.toFixed(2)}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums">{currency(h.total_value)}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums"><Delta value={h.gain_loss_percentage} /></td>
                        <td className="px-4 py-2.5 text-right">
                          {pendingDelete === h.id ? (
                            <div className="flex justify-end gap-1.5">
                              <Button variant="danger" onClick={() => handleDelete(h.id)}>Remove</Button>
                              <Button variant="ghost" onClick={() => setPendingDelete(null)}>Cancel</Button>
                            </div>
                          ) : (
                            <div className="flex justify-end gap-1">
                              <button
                                onClick={() => {
                                  setEditingId(h.id);
                                  setEditShares(String(h.shares));
                                  setEditPrice(String(h.average_buy_price));
                                }}
                                aria-label={`Edit ${h.symbol}`}
                                className="p-1 text-mutedText hover:text-foreground"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => setPendingDelete(h.id)}
                                aria-label={`Remove ${h.symbol}`}
                                className="p-1 text-mutedText hover:text-bearish"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          )}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
                {!isLoading && holdings.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-mutedText text-sm">
                      No holdings yet — import from Groww or add a position above. This is optional;
                      you can research any stock in chat without a portfolio.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
