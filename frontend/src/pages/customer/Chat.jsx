import { useEffect, useRef, useState } from "react";
import client from "../../api/client";

const AGENT_LABEL = {
  query_agent: "Query Agent",
  order_agent: "Order Agent",
  complaint_agent: "Complaint Agent",
  handoff: "Human Handoff",
  system: "System",
};

export default function Chat() {
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadConversations() {
    const res = await client.get("/chat/conversations");
    setConversations(res.data.conversations);
  }

  async function openConversation(id) {
    setConversationId(id);
    const res = await client.get(`/chat/conversations/${id}/messages`);
    setMessages(res.data.messages);
  }

  function startNewChat() {
    setConversationId(null);
    setMessages([]);
  }

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    setError("");
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text, created_at: new Date().toISOString(), _pending: true }]);
    setSending(true);
    try {
      const res = await client.post("/chat/message", { message: text, conversation_id: conversationId });
      const data = res.data;
      setConversationId(data.conversation_id);
      setMessages((m) => [
        ...m,
        {
          role: "agent",
          content: data.reply,
          created_at: new Date().toISOString(),
          meta: { agent: data.agent, actions: data.actions, sentiment: data.sentiment, intent: data.intent },
        },
      ]);
      loadConversations();
    } catch (err) {
      setError(err.response?.data?.error || "Something went wrong sending your message.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-4">
      <div className="w-56 flex-shrink-0 overflow-y-auto card p-3">
        <button onClick={startNewChat} className="btn-outline mb-3 w-full text-xs">
          + New conversation
        </button>
        <div className="space-y-1">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => openConversation(c.id)}
              className={`block w-full truncate rounded px-2 py-1.5 text-left text-xs ${
                conversationId === c.id ? "bg-teal-light text-teal-dark" : "text-slate hover:bg-paper"
              }`}
            >
              {c.status === "escalated" ? "🔴 " : "💬 "}
              {c.last_intent ? c.last_intent.replace(/_/g, " ") : "New chat"}
            </button>
          ))}
          {conversations.length === 0 && <p className="px-2 text-xs text-slate">No conversations yet.</p>}
        </div>
      </div>

      <div className="flex flex-1 flex-col card">
        <div className="border-b border-line px-5 py-3">
          <h2 className="text-sm font-semibold">AI Support Chat</h2>
          <p className="text-xs text-slate">
            Ask about orders, cancellations, complaints, or general questions — routed automatically.
          </p>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center text-slate">
              <p className="text-sm">Start a conversation. Try:</p>
              <p className="mt-2 font-mono text-xs">"Where is my order?" · "I want to cancel ORD-12345678"</p>
              <p className="font-mono text-xs">"My package arrived broken" · "What's your return policy?"</p>
            </div>
          )}
          {messages.map((m, idx) => (
            <div key={idx} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[75%] ${m.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
                <div
                  className={`rounded-lg px-3.5 py-2.5 text-sm ${
                    m.role === "user" ? "bg-ink text-paper" : "border border-line bg-paper text-ink"
                  }`}
                >
                  {m.content}
                </div>
                {m.meta?.agent && (
                  <div className="mt-1 flex flex-wrap items-center gap-1.5 px-1 text-[11px] text-slate">
                    <span className="badge bg-teal-light text-teal-dark">{AGENT_LABEL[m.meta.agent] || m.meta.agent}</span>
                    {m.meta.actions?.includes("escalated") && (
                      <span className="badge bg-coral-light text-coral">Escalated</span>
                    )}
                    {m.meta.actions?.includes("order_cancelled") && (
                      <span className="badge bg-teal-light text-teal-dark">Order cancelled</span>
                    )}
                    {m.meta.actions?.includes("ticket_created") && (
                      <span className="badge bg-amber-light text-amber">Ticket created</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {sending && <p className="text-xs text-slate">Aria is thinking…</p>}
          <div ref={bottomRef} />
        </div>

        {error && <p className="border-t border-line bg-coral-light px-5 py-2 text-xs text-coral">{error}</p>}

        <div className="flex items-center gap-2 border-t border-line px-4 py-3">
          <input
            className="input"
            placeholder="Type your message…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button className="btn-primary" onClick={send} disabled={sending}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
