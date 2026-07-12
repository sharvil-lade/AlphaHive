"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Star } from "lucide-react";
import { useSessionId } from "../../hooks/useSessionId";
import { fetchWatchlist, addToWatchlist, deleteFromWatchlist } from "../../services/api";
import { Card, Button, Input, PageHeader } from "../../components/ui/primitives";

export default function WatchlistPage() {
  const sessionId = useSessionId();
  const queryClient = useQueryClient();
  const [symbol, setSymbol] = useState("");

  const { data: watchlist = [] } = useQuery({
    queryKey: ["watchlist", sessionId],
    queryFn: () => fetchWatchlist(sessionId),
    enabled: !!sessionId,
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["watchlist", sessionId] });

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol) return;
    await addToWatchlist(sessionId, symbol.toUpperCase().trim());
    setSymbol("");
    refresh();
  };

  const handleRemove = async (sym: string) => {
    await deleteFromWatchlist(sessionId, sym);
    refresh();
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader title="Watchlist" description="Symbols you're tracking" />

      <div className="flex-1 overflow-y-auto p-6 max-w-3xl w-full mx-auto space-y-4">
        <Card>
          <form onSubmit={handleAdd} className="flex gap-2">
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="Add a symbol, e.g. TCS or AAPL"
              className="flex-1"
            />
            <Button type="submit">
              <Plus className="w-3.5 h-3.5" /> Add
            </Button>
          </form>
        </Card>

        <div className="space-y-2">
          {watchlist.map((w: any) => (
            <div
              key={w.id}
              className="flex items-center justify-between bg-surface border border-surface-border rounded-lg px-4 py-3"
            >
              <div className="flex items-center gap-2.5">
                <Star className="w-4 h-4 text-mutedText" />
                <span className="font-medium text-sm">{w.symbol}</span>
              </div>
              <button onClick={() => handleRemove(w.symbol)} className="p-1 text-mutedText hover:text-bearish">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
          {watchlist.length === 0 && (
            <div className="text-center text-mutedText text-sm py-8">
              Your watchlist is empty — add a symbol above.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
