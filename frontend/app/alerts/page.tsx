"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, BellRing, PlayCircle } from "lucide-react";
import { useSessionId } from "../../hooks/useSessionId";
import { fetchAlerts, createAlert, deleteAlert, runAlertCheck } from "../../services/api";
import { Card, Button, Input, Select, PageHeader } from "../../components/ui/primitives";

const TRIGGER_TYPES = [
  { value: "price_above", label: "Price above" },
  { value: "price_below", label: "Price below" },
  { value: "rsi_above", label: "RSI above" },
  { value: "rsi_below", label: "RSI below" },
  { value: "sentiment_drop", label: "Sentiment drop below" },
];

export default function AlertsPage() {
  const sessionId = useSessionId();
  const queryClient = useQueryClient();
  const [symbol, setSymbol] = useState("");
  const [triggerType, setTriggerType] = useState("price_above");
  const [triggerValue, setTriggerValue] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);
  const [triggeredLog, setTriggeredLog] = useState<any[]>([]);

  const { data: alerts = [] } = useQuery({
    queryKey: ["alerts", sessionId, activeOnly],
    queryFn: () => fetchAlerts(sessionId, activeOnly),
    enabled: !!sessionId,
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["alerts", sessionId, activeOnly] });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol || !triggerValue) return;
    await createAlert(sessionId, symbol.toUpperCase().trim(), triggerType, parseFloat(triggerValue));
    setSymbol("");
    setTriggerValue("");
    refresh();
  };

  const handleDelete = async (alertId: string) => {
    await deleteAlert(sessionId, alertId);
    refresh();
  };

  const handleCheck = async () => {
    const triggered = await runAlertCheck();
    if (triggered?.length) setTriggeredLog((prev) => [...triggered, ...prev]);
    refresh();
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader title="Alerts" description="Rules-based price, RSI, and sentiment alerts" />

      <div className="flex-1 overflow-y-auto p-6 max-w-3xl w-full mx-auto space-y-4">
        <Card>
          <form onSubmit={handleCreate} className="flex flex-wrap gap-2 items-end">
            <div>
              <label className="text-[11px] text-mutedText block mb-1">Symbol</label>
              <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="RELIANCE" />
            </div>
            <div>
              <label className="text-[11px] text-mutedText block mb-1">Trigger</label>
              <Select value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
                {TRIGGER_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </Select>
            </div>
            <div>
              <label className="text-[11px] text-mutedText block mb-1">Value</label>
              <Input value={triggerValue} onChange={(e) => setTriggerValue(e.target.value)} type="number" placeholder="1300" />
            </div>
            <Button type="submit"><Plus className="w-3.5 h-3.5" /> Create alert</Button>
            <Button type="button" variant="outline" onClick={handleCheck}>
              <PlayCircle className="w-3.5 h-3.5" /> Run check now
            </Button>
          </form>
        </Card>

        <label className="flex items-center gap-2 text-sm text-mutedText">
          <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />
          Active only
        </label>

        <div className="space-y-2">
          {alerts.map((a: any) => (
            <div key={a.id} className="flex items-center justify-between bg-surface border border-surface-border rounded-lg px-4 py-3">
              <div className="flex items-center gap-2.5 text-sm">
                <BellRing className="w-4 h-4 text-mutedText" />
                <span className="font-medium">{a.symbol}</span>
                <span className="text-mutedText">
                  {TRIGGER_TYPES.find((t) => t.value === a.trigger_type)?.label ?? a.trigger_type} {a.trigger_value}
                </span>
              </div>
              <button onClick={() => handleDelete(a.id)} className="p-1 text-mutedText hover:text-bearish">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
          {alerts.length === 0 && (
            <div className="text-center text-mutedText text-sm py-8">No alerts configured yet.</div>
          )}
        </div>

        {triggeredLog.length > 0 && (
          <div>
            <h2 className="text-sm font-medium text-mutedText mb-2">Recently triggered</h2>
            <div className="space-y-1.5">
              {triggeredLog.map((t, i) => (
                <div key={i} className="text-xs text-bearish bg-bearish/10 border border-bearish/20 rounded-md px-3 py-2">
                  {JSON.stringify(t)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
