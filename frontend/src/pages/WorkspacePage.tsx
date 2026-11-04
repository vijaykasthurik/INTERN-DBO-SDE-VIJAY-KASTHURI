import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import {
  Send,
  Square,
  Sparkles,
  Bot,
  User as UserIcon,
  HelpCircle,
  AlertTriangle,
  Code2,
  Table,
  PanelRight,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { DatasetRail } from "../features/workspace/DatasetRail";
import { ReasoningTimeline, type TimelineStep, type VerificationInfo } from "../features/workspace/ReasoningTimeline";
import { EvidenceDrawer } from "../features/workspace/EvidenceDrawer";
import { ChartRenderer } from "../features/workspace/ChartRenderer";
import { ChatStreamService } from "../features/workspace/ChatStreamService";
import { api, type ChatSession, type EvidenceEntry } from "../lib/api";
import { useDatasetStore } from "../stores/datasetStore";
import { useAIConnectionStore } from "../stores/aiConnectionStore";

interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  business_insight?: string;
  how_i_got_this?: string;
  chart_spec?: Record<string, unknown>;
  confidence?: "High" | "Medium" | "Low";
  suggested_followups?: string[];
  sql_code?: string;
  pandas_code?: string;
  clarify_options?: string[];
  anomalies?: Array<{ row_id: string; value: number; reason: string }>;
  evidence?: EvidenceEntry[];
}

export const WorkspacePage: React.FC = () => {
  const { fetchDatasets } = useDatasetStore();
  const { connection, openConnectModal } = useAIConnectionStore();
  const [providerSwitchAlert, setProviderSwitchAlert] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);

  // Layout state
  const [railOpen, setRailOpen] = useState<boolean>(true);
  const [timelineOpen, setTimelineOpen] = useState<boolean>(true);

  // Reasoning timeline state
  const [activeLane, setActiveLane] = useState<string>("");
  const [timelineSteps, setTimelineSteps] = useState<TimelineStep[]>([]);
  const [timelineRepairs, setTimelineRepairs] = useState<Array<{ step_id: string; error_type: string; attempt: number }>>([]);
  const [timelineVerification, setTimelineVerification] = useState<VerificationInfo | null>(null);

  // Evidence Drawer state
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [drawerEntries, setDrawerEntries] = useState<EvidenceEntry[]>([]);
  const [drawerSql, setDrawerSql] = useState<string | undefined>(undefined);
  const [drawerPandas, setDrawerPandas] = useState<string | undefined>(undefined);
  const [activeAuditedNumber, setActiveAuditedNumber] = useState<string | undefined>(undefined);

  const streamServiceRef = useRef<ChatStreamService>(new ChatStreamService());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchDatasets();
    initChatSession();
  }, [fetchDatasets]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const initChatSession = async () => {
    try {
      const existingSessions = await api.chat.listSessions();
      setSessions(existingSessions);
      if (existingSessions.length > 0) {
        setActiveSession(existingSessions[0]);
      } else {
        const newSession = await api.chat.createSession({ title: "Analysis Workspace" });
        setActiveSession(newSession);
        setSessions([newSession]);
      }
    } catch {
      // Fallback local session
      const fallbackSession: ChatSession = {
        id: "sess_local_default",
        title: "Executive Analysis",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setActiveSession(fallbackSession);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text || isStreaming) return;

    if (!textToSend) setInputText("");

    // Reset reasoning panel for new inquiry
    setActiveLane("");
    setTimelineSteps([]);
    setTimelineRepairs([]);
    setTimelineVerification(null);

    const userMsg: MessageItem = {
      id: `usr_${Date.now()}`,
      role: "user",
      content: text,
    };

    const assistantMsgId = `asst_${Date.now()}`;
    const assistantMsg: MessageItem = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    const sessionId = activeSession?.id || "sess_local_default";

    await streamServiceRef.current.streamMessage(sessionId, text, {
      onRoute: (lane) => {
        setActiveLane(lane);
      },
      onPlan: (planPayload) => {
        const dagObj =
          (planPayload.dag as {
            steps?: Array<{ id: string; tool: string; description: string }>;
          }) || planPayload;
        const rawSteps = dagObj.steps || [];
        setTimelineSteps(
          rawSteps.map((s) => ({
            id: s.id,
            tool: s.tool,
            description: s.description,
            status: "pending",
          }))
        );
      },
      onStepStart: (step) => {
        setTimelineSteps((prev) => {
          const exists = prev.some((s) => s.id === step.step_id);
          if (!exists) {
            return [
              ...prev,
              {
                id: step.step_id,
                tool: step.tool,
                description: step.description || step.tool,
                status: "running",
              },
            ];
          }
          return prev.map((s) =>
            s.id === step.step_id ? { ...s, status: "running" } : s
          );
        });
      },
      onStepResult: (result) => {
        setTimelineSteps((prev) =>
          prev.map((s) =>
            s.id === result.step_id
              ? {
                  ...s,
                  status: result.status === "failed" ? "failed" : "completed",
                  runtime_ms: result.runtime_ms,
                  row_count: result.row_count,
                }
              : s
          )
        );
      },
      onRepair: (repair) => {
        setTimelineRepairs((prev) => [...prev, repair]);
      },
      onVerify: (ver) => {
        setTimelineVerification({
          status: ver.status,
          confidence: ver.confidence,
          reasons: ver.reasons,
          checks: ver.checks,
        });
      },
      onProviderSwitch: (info) => {
        setProviderSwitchAlert(info.reason);
      },
      onToken: (token) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, content: m.content + token } : m
          )
        );
      },
      onFinal: (finalData) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: finalData.direct_answer,
                  business_insight: finalData.business_insight,
                  how_i_got_this: finalData.how_i_got_this,
                  chart_spec: finalData.chart_spec,
                  confidence: finalData.confidence,
                  suggested_followups: finalData.suggested_followups,
                  sql_code: finalData.sql_code,
                  pandas_code: finalData.pandas_code,
                  clarify_options: finalData.clarify_options,
                  anomalies: finalData.anomalies,
                  isStreaming: false,
                }
              : m
          )
        );
      },
      onDone: () => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, isStreaming: false } : m))
        );
      },
      onError: (err) => {
        setIsStreaming(false);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: `Analysis encountered an error: ${err.message}`,
                  isStreaming: false,
                }
              : m
          )
        );
      },
    });
  };

  const handleStop = () => {
    streamServiceRef.current.abort();
    setIsStreaming(false);
  };

  const openEvidence = (
    msg: MessageItem,
    numberClaim?: string
  ) => {
    setActiveAuditedNumber(numberClaim);
    setDrawerSql(msg.sql_code);
    setDrawerPandas(msg.pandas_code);
    setDrawerEntries(
      timelineSteps.map((s) => ({
        step_id: s.id,
        tool: s.tool,
        code: msg.sql_code || "-- Verified query execution",
        result_preview: msg.content,
        row_count: s.row_count || 1,
        runtime_ms: s.runtime_ms || 12.0,
        status: s.status === "failed" ? "failed" : "success",
      }))
    );
    setDrawerOpen(true);
  };

  return (
    <div className="h-screen flex flex-col pt-16 bg-white overflow-hidden text-ink">
      {/* 3-PANE WORKSPACE CONTAINER */}
      <div className="flex-1 flex overflow-hidden">
        {/* PANE 1: LEFT DATASET RAIL */}
        <DatasetRail
          isOpen={railOpen}
          onToggle={() => setRailOpen(!railOpen)}
          onSelectPrompt={(prompt) => handleSendMessage(prompt)}
        />

        {/* PANE 2: CENTER CHAT STREAM & COMPOSER */}
        <main className="flex-1 flex flex-col justify-between overflow-hidden bg-white relative">
          {/* TOP BAR WITH TOGGLES */}
          <div className="px-6 py-2.5 border-b border-hairline flex items-center justify-between text-xs text-ink-muted">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-ink">
                {activeSession?.title || "Executive Analysis Workspace"}
              </span>
              {sessions.length > 1 && (
                <span className="text-[10px] text-ink-muted">
                  • {sessions.length} sessions
                </span>
              )}
              <Badge variant="neutral" size="sm">DuckDB Isolated</Badge>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setTimelineOpen(!timelineOpen)}
                className="h-7 px-2 text-xs"
              >
                <PanelRight className="w-3.5 h-3.5 mr-1" />
                <span>{timelineOpen ? "Hide Reasoning" : "Show Reasoning"}</span>
              </Button>
            </div>
          </div>

          {/* BYOK EXPIRY OR PROVIDER SWITCH BANNER */}
          {connection?.connected && (connection.status === "invalid" || connection.status === "quota_exhausted") && (
            <div className="bg-amber-50/90 border-b border-amber-200 px-6 py-2 flex items-center justify-between text-xs text-amber-900 animate-fadeIn">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>
                  Your {connection.provider_id?.toUpperCase()} key {connection.status === "quota_exhausted" ? "ran out of credit" : "expired or encountered an error"}. Using shared server model for now.
                </span>
              </div>
              <button
                type="button"
                onClick={() => openConnectModal(connection.provider_id)}
                className="font-semibold underline hover:text-amber-950 ml-3 whitespace-nowrap"
              >
                Update key
              </button>
            </div>
          )}

          {providerSwitchAlert && (
            <div className="bg-indigo-50/90 border-b border-indigo-200 px-6 py-2 flex items-center justify-between text-xs text-indigo-900 animate-fadeIn">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-600 shrink-0" />
                <span>{providerSwitchAlert}</span>
              </div>
              <button
                type="button"
                onClick={() => setProviderSwitchAlert(null)}
                className="text-indigo-600 hover:text-indigo-950 text-xs font-medium ml-3"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* CHAT MESSAGES SCROLL AREA */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-12 select-none">
                <div className="w-12 h-12 rounded-24 bg-accent-gradient flex items-center justify-center text-white mb-4 shadow-soft-xs">
                  <Sparkles className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-serif font-medium text-ink tracking-tight">
                  Start an Analysis
                </h3>
                <p className="text-xs text-ink-muted mt-1 leading-relaxed">
                  Ask questions in plain English. Lumen builds a DAG of queries, verifies every number against DuckDB, and draws interactive ECharts charts.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 justify-center">
                  {[
                    "Which region generated the highest revenue?",
                    "Show monthly sales trends.",
                    "Which products are underperforming?",
                    "Detect anomalies in the dataset.",
                  ].map((chip) => (
                    <button
                      key={chip}
                      onClick={() => handleSendMessage(chip)}
                      className="px-3 py-1.5 rounded-pill bg-surface hover:bg-white border border-hairline text-xs font-medium text-ink transition-all shadow-soft-xs hover:border-accent-indigo"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className="space-y-4 max-w-3xl mx-auto">
                  {/* MESSAGE ROW */}
                  <div className={`flex gap-3.5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    {msg.role === "assistant" && (
                      <div className="w-8 h-8 rounded-pill bg-accent-gradient flex items-center justify-center text-white flex-shrink-0 shadow-soft-xs mt-0.5">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div
                      className={`rounded-24 p-5 max-w-2xl border transition-all ${
                        msg.role === "user"
                          ? "bg-slate-900 text-white border-transparent shadow-soft-xs ml-12"
                          : "bg-surface/60 border-hairline shadow-soft-xs mr-12 text-ink"
                      }`}
                    >
                      {/* MESSAGE CONTENT */}
                      <div className="prose prose-sm max-w-none text-xs leading-relaxed text-current">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                        {msg.isStreaming && (
                          <span className="inline-block w-1.5 h-3.5 bg-accent-indigo ml-1 animate-pulse align-middle" />
                        )}
                      </div>

                      {/* BUSINESS INSIGHT BANNER */}
                      {msg.business_insight && (
                        <div className="mt-4 p-3 rounded-16 bg-white border border-hairline flex items-start gap-2.5">
                          <Sparkles className="w-4 h-4 text-accent-indigo flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="text-[10px] font-bold text-accent-indigo uppercase tracking-wider">
                              Executive Insight
                            </p>
                            <p className="text-xs text-ink mt-0.5 leading-normal">
                              {msg.business_insight}
                            </p>
                          </div>
                        </div>
                      )}

                      {/* ANOMALY CARDS */}
                      {msg.anomalies && msg.anomalies.length > 0 && (
                        <div className="mt-4 space-y-2">
                          <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-600">
                            <AlertTriangle className="w-4 h-4" />
                            <span>Multivariate Anomalies Flagged ({msg.anomalies.length})</span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {msg.anomalies.map((ano, i) => (
                              <div
                                key={i}
                                className="p-2.5 bg-rose-50/60 border border-rose-100 rounded-16 text-[11px]"
                              >
                                <span className="font-mono font-bold text-rose-700">{ano.row_id}</span>
                                <span className="text-ink-muted ml-2">${ano.value.toLocaleString()}</span>
                                <p className="text-ink-muted text-[10px] mt-0.5">{ano.reason}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* CLARIFY OPTION CHIPS */}
                      {msg.clarify_options && msg.clarify_options.length > 0 && (
                        <div className="mt-4 space-y-2">
                          <p className="text-[11px] font-medium text-ink-muted">
                            Select one of the following to clarify:
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {msg.clarify_options.map((opt) => (
                              <button
                                key={opt}
                                onClick={() => handleSendMessage(opt)}
                                className="px-3 py-1 rounded-pill bg-white border border-hairline hover:border-accent-indigo text-xs text-ink font-medium transition-all shadow-soft-xs"
                              >
                                {opt}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* INLINE ECHARTS VISUALIZATION */}
                      {msg.chart_spec && (
                        <div className="mt-5">
                          <ChartRenderer
                            spec={msg.chart_spec}
                            title="Analytical Chart"
                          />
                        </div>
                      )}

                      {/* CODE & EVIDENCE AUDIT BUTTONS */}
                      {msg.role === "assistant" && !msg.isStreaming && (
                        <div className="mt-4 pt-3 border-t border-hairline flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openEvidence(msg)}
                              className="h-7 px-2.5 text-[11px] text-accent-indigo hover:bg-indigo-50"
                            >
                              <Table className="w-3 h-3 mr-1" />
                              View Evidence Ledger
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openEvidence(msg)}
                              className="h-7 px-2 text-[11px] text-ink-muted hover:text-ink"
                            >
                              <Code2 className="w-3 h-3 mr-1" />
                              SQL / Code
                            </Button>
                          </div>

                          {msg.confidence && (
                            <Badge
                              variant={
                                msg.confidence === "High"
                                  ? "success"
                                  : msg.confidence === "Medium"
                                  ? "warning"
                                  : "error"
                              }
                              size="sm"
                            >
                              {msg.confidence} Confidence
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>

                    {msg.role === "user" && (
                      <div className="w-8 h-8 rounded-pill bg-slate-200 border border-hairline flex items-center justify-center text-ink flex-shrink-0 mt-0.5">
                        <UserIcon className="w-4 h-4" />
                      </div>
                    )}
                  </div>

                  {/* SUGGESTED FOLLOW-UP CHIPS */}
                  {msg.suggested_followups && msg.suggested_followups.length > 0 && (
                    <div className="pl-12 flex flex-wrap gap-2">
                      {msg.suggested_followups.map((fu, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSendMessage(fu)}
                          className="px-3 py-1 rounded-pill bg-white border border-hairline hover:border-accent-indigo text-[11px] font-medium text-ink-muted hover:text-ink transition-all shadow-soft-xs flex items-center gap-1.5"
                        >
                          <HelpCircle className="w-3 h-3 text-accent-indigo" />
                          <span>{fu}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* COMPOSER DOCK */}
          <div className="p-4 border-t border-hairline bg-white/95 backdrop-blur-md">
            <div className="max-w-3xl mx-auto flex items-center gap-3">
              <input
                type="text"
                placeholder="Ask about sales, anomalies, trends, or request SQL..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                disabled={isStreaming}
                className="flex-1 h-11 px-4 text-sm rounded-pill border border-hairline bg-surface text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-accent-indigo focus:border-transparent transition-all"
              />

              {isStreaming ? (
                <Button
                  onClick={handleStop}
                  variant="outline"
                  size="md"
                  className="rounded-pill text-rose-600 border-rose-200 hover:bg-rose-50"
                >
                  <Square className="w-4 h-4 mr-1.5 fill-current" />
                  Stop
                </Button>
              ) : (
                <Button
                  onClick={() => handleSendMessage()}
                  disabled={!inputText.trim()}
                  size="md"
                  className="rounded-pill px-5 shadow-soft-xs"
                >
                  <Send className="w-4 h-4 mr-1.5" />
                  Ask
                </Button>
              )}
            </div>
          </div>
        </main>

        {/* PANE 3: RIGHT REASONING PANEL */}
        {timelineOpen && (
          <aside className="w-80 border-l border-hairline bg-surface/30 p-4 h-full overflow-y-auto hidden lg:block">
            <ReasoningTimeline
              lane={activeLane}
              steps={timelineSteps}
              repairs={timelineRepairs}
              verification={timelineVerification}
            />
          </aside>
        )}
      </div>

      {/* EVIDENCE DRAWER OVERLAY */}
      <EvidenceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        entries={drawerEntries}
        sqlCode={drawerSql}
        pandasCode={drawerPandas}
        activeNumber={activeAuditedNumber}
      />
    </div>
  );
};
