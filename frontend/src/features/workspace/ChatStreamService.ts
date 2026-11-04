/**
 * Lumen Streaming SSE Chat Client
 * Uses fetch + ReadableStream with AbortController for clean lifecycle management.
 */

export interface SSEEvent {
  event_type:
    | "route"
    | "plan"
    | "step_start"
    | "step_result"
    | "repair"
    | "verify"
    | "chart"
    | "token"
    | "final"
    | "error"
    | "done"
    | "provider_switch";
  trace_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface StreamCallbacks {
  onEvent?: (event: SSEEvent) => void;
  onRoute?: (route: string) => void;
  onPlan?: (plan: Record<string, unknown>) => void;
  onStepStart?: (step: { step_id: string; tool: string; description?: string }) => void;
  onStepResult?: (result: { step_id: string; status: string; runtime_ms?: number; row_count?: number; result_preview?: unknown }) => void;
  onRepair?: (repair: { step_id: string; error_type: string; attempt: number }) => void;
  onVerify?: (verification: { status: string; confidence: "High" | "Medium" | "Low"; reasons: string[]; checks: Record<string, boolean> }) => void;
  onChart?: (spec: Record<string, unknown>) => void;
  onToken?: (token: string) => void;
  onProviderSwitch?: (switchInfo: { reason: string; from_provider: string; to_provider: string }) => void;
  onFinal?: (finalData: {
    direct_answer: string;
    business_insight?: string;
    how_i_got_this?: string;
    chart_spec?: Record<string, unknown>;
    confidence?: "High" | "Medium" | "Low";
    suggested_followups?: string[];
    sql_code?: string;
    pandas_code?: string;
    clarify_options?: string[];
    anomalies?: Array<{ row_id: string; value: number; reason: string }>;
  }) => void;
  onError?: (err: Error) => void;
  onDone?: () => void;
}

export class ChatStreamService {
  private abortController: AbortController | null = null;

  public async streamMessage(
    sessionId: string,
    content: string,
    callbacks: StreamCallbacks
  ): Promise<void> {
    this.abortController = new AbortController();
    const token = localStorage.getItem("lumen_access_token");

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        headers,
        body: JSON.stringify({ content }),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        let errText = await response.text().catch(() => "");
        throw new Error(`Chat stream request failed (${response.status}): ${errText}`);
      }

      if (!response.body) {
        throw new Error("Response body is not readable");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            const rawJson = trimmed.slice(6).trim();
            if (rawJson) {
              try {
                const parsed: SSEEvent = JSON.parse(rawJson);
                this.dispatch(parsed, callbacks);
              } catch (e) {
                console.warn("Could not parse SSE JSON line:", trimmed, e);
              }
            }
          }
        }
      }

      callbacks.onDone?.();
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        callbacks.onDone?.();
        return;
      }
      const errorObj = err instanceof Error ? err : new Error(String(err));
      callbacks.onError?.(errorObj);
    } finally {
      this.abortController = null;
    }
  }

  public abort(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  private dispatch(event: SSEEvent, callbacks: StreamCallbacks): void {
    callbacks.onEvent?.(event);
    const p = event.payload;

    switch (event.event_type) {
      case "route":
        callbacks.onRoute?.(String(p.lane || p.route || ""));
        break;
      case "plan":
        callbacks.onPlan?.(p);
        break;
      case "step_start":
        callbacks.onStepStart?.({
          step_id: String(p.step_id || ""),
          tool: String(p.tool || ""),
          description: String(p.description || ""),
        });
        break;
      case "step_result":
        callbacks.onStepResult?.({
          step_id: String(p.step_id || ""),
          status: String(p.status || "success"),
          runtime_ms: typeof p.runtime_ms === "number" ? p.runtime_ms : undefined,
          row_count: typeof p.row_count === "number" ? p.row_count : undefined,
          result_preview: p.result_preview,
        });
        break;
      case "repair":
        callbacks.onRepair?.({
          step_id: String(p.step_id || ""),
          error_type: String(p.error_type || ""),
          attempt: typeof p.attempt === "number" ? p.attempt : 1,
        });
        break;
      case "verify":
        callbacks.onVerify?.({
          status: String(p.status || "verified"),
          confidence: (p.confidence as "High" | "Medium" | "Low") || "High",
          reasons: Array.isArray(p.reasons) ? p.reasons.map(String) : [],
          checks: (p.checks as Record<string, boolean>) || {},
        });
        break;
      case "chart":
        callbacks.onChart?.(p);
        break;
      case "token":
        callbacks.onToken?.(String(p.token || ""));
        break;
      case "final":
        callbacks.onFinal?.({
          direct_answer: String(p.direct_answer || ""),
          business_insight: p.business_insight ? String(p.business_insight) : undefined,
          how_i_got_this: p.how_i_got_this ? String(p.how_i_got_this) : undefined,
          chart_spec: (p.chart_spec as Record<string, unknown>) || undefined,
          confidence: (p.confidence as "High" | "Medium" | "Low") || undefined,
          suggested_followups: Array.isArray(p.suggested_followups)
            ? p.suggested_followups.map(String)
            : undefined,
          sql_code: p.sql_code ? String(p.sql_code) : undefined,
          pandas_code: p.pandas_code ? String(p.pandas_code) : undefined,
          clarify_options: Array.isArray(p.clarify_options)
            ? p.clarify_options.map(String)
            : undefined,
          anomalies: Array.isArray(p.anomalies)
            ? (p.anomalies as Array<{ row_id: string; value: number; reason: string }>)
            : undefined,
        });
        break;
      case "provider_switch":
        callbacks.onProviderSwitch?.({
          reason: String(p.reason || ""),
          from_provider: String(p.from_provider || ""),
          to_provider: String(p.to_provider || ""),
        });
        break;
      case "done":
        callbacks.onDone?.();
        break;
      case "error":
        callbacks.onError?.(new Error(String(p.error || "Unknown stream error")));
        break;
    }
  }
}
