import { useEffect, useRef } from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface StreamLog {
  node: string;
  message: string;
  timestamp: string;
  done?: boolean;
}

export function useAgentStream(
  runId: string | null,
  onLog: (log: StreamLog) => void,
  onDone: (status: string) => void,
  onError?: (err: any) => void
) {
  // Store callbacks in refs to avoid restarting EventSource if handlers change
  const onLogRef = useRef(onLog);
  const onDoneRef = useRef(onDone);
  const onErrorRef = useRef(onError);

  onLogRef.current = onLog;
  onDoneRef.current = onDone;
  onErrorRef.current = onError;

  useEffect(() => {
    if (!runId) return;

    const streamUrl = `${API_BASE_URL}/api/v1/agents/run/${runId}/stream`;
    const eventSource = new EventSource(streamUrl);

    eventSource.onmessage = (event) => {
      try {
        const data: StreamLog = JSON.parse(event.data);
        if (data.done) {
          onDoneRef.current(data.message);
          eventSource.close();
        } else {
          onLogRef.current(data);
        }
      } catch (err) {
        console.error('Failed to parse SSE streaming log:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE EventSource error:', err);
      if (onErrorRef.current) {
        onErrorRef.current(err);
      }
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [runId]);
}
