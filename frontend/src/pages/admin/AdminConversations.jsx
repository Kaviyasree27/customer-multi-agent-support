import { useEffect, useState } from "react";
import client from "../../api/client";
import StatusBadge from "../../components/StatusBadge";

export default function AdminConversations() {
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const res = await client.get("/admin/conversations");
    setConversations(res.data.conversations);
  }

  async function open(c) {
    setSelected(c);
    const res = await client.get(`/admin/conversations/${c.id}/messages`);
    setMessages(res.data.messages);
  }

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">AI conversations</h1>
      <p className="mb-6 text-sm text-slate">Monitor live agent activity across all customers.</p>

      <div className="grid grid-cols-5 gap-6">
        <div className="col-span-2 space-y-2">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => open(c)}
              className={`card block w-full p-3 text-left ${selected?.id === c.id ? "border-teal" : ""}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium capitalize">{c.last_intent?.replace(/_/g, " ") || "New"}</span>
                <StatusBadge value={c.status} />
              </div>
              <p className="mt-1 text-xs text-slate">Updated {new Date(c.updated_at).toLocaleString()}</p>
            </button>
          ))}
          {conversations.length === 0 && <p className="card p-4 text-xs text-slate">No conversations yet.</p>}
        </div>

        <div className="col-span-3">
          {!selected ? (
            <p className="card p-6 text-center text-sm text-slate">Select a conversation to inspect.</p>
          ) : (
            <div className="card max-h-[70vh] space-y-3 overflow-y-auto p-4">
              {messages.map((m) => (
                <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className="max-w-[80%]">
                    <div
                      className={`rounded-lg px-3 py-2 text-sm ${
                        m.role === "user" ? "bg-ink text-paper" : "border border-line bg-paper"
                      }`}
                    >
                      {m.content}
                    </div>
                    {m.meta?.agent && (
                      <p className="mt-1 px-1 text-[11px] text-slate">
                        {m.meta.agent}
                        {m.meta.sentiment && ` · sentiment ${m.meta.sentiment.sentiment_score}`}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
