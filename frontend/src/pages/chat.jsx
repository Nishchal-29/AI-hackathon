// src/pages/chat.jsx
import React, { useState, useRef } from "react";
import { Link } from "react-router-dom";
const API_BASE = "http://127.0.0.1:8000"; // e.g. "http://127.0.0.1:8000" or "" when proxied

export const Chat = () => {
  // Build index form state
  const [csvPath, setCsvPath] = useState("/mnt/data/dgms_accidents.csv");
  const [chunkPer, setChunkPer] = useState(1);
  const [forceRecreate, setForceRecreate] = useState(false);
  const [namespace, setNamespace] = useState("");
  const [buildLoading, setBuildLoading] = useState(false);
  const [buildMessage, setBuildMessage] = useState(null);

  // Chat state
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(6);
  const [loadingQuery, setLoadingQuery] = useState(false);
  const [messages, setMessages] = useState([]); // {role: 'user'|'bot' , text, meta?}
  const messagesEndRef = useRef(null);

  function scrollToBottom() {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }

  async function handleBuildIndex(e) {
    e && e.preventDefault();
    setBuildLoading(true);
    setBuildMessage(null);

    try {
      const payload = {
        csv_path: csvPath,
        chunk_per_n_rows: Number(chunkPer) || 1,
        force_recreate: Boolean(forceRecreate),
        namespace: namespace || ""
      };

      const res = await fetch(`${API_BASE}/build-index`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Build failed: ${res.status} ${txt}`);
      }
      const j = await res.json();
      setBuildMessage({ ok: true, text: j.message || "Index build started" });
    } catch (err) {
      console.error("Build error", err);
      setBuildMessage({ ok: false, text: err.message || String(err) });
    } finally {
      setBuildLoading(false);
    }
  }

  async function handleSendQuestion(e) {
    e && e.preventDefault();
    const q = question.trim();
    if (!q) return;
    // append user's message
    const userMsg = { role: "user", text: q, ts: Date.now() };
    setMessages((m) => [...m, userMsg]);
    setQuestion("");
    setLoadingQuery(true);

    try {
      const payload = {
        question: q,
        top_k: 43,
        namespace: namespace || ""
      };

      const res = await fetch(`${API_BASE}/query-rag`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        // try to show body
        const txt = await res.text();
        throw new Error(`Query failed: ${res.status} ${txt}`);
      }

      const j = await res.json();
      // API returns { status: "ok", question, answer }
      const answer = j.answer ?? j;
      const botMsg = { role: "bot", text: typeof answer === "string" ? answer : JSON.stringify(answer, null, 2), ts: Date.now() };
      setMessages((m) => [...m, botMsg]);
      scrollToBottom();
    } catch (err) {
      console.error("Query error", err);
      const errMsg = { role: "bot", text: `Error: ${err.message}`, ts: Date.now() };
      setMessages((m) => [...m, errMsg]);
      scrollToBottom();
    } finally {
      setLoadingQuery(false);
    }
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div>
          <Link to="/" style={styles.linkBack}>&larr; Home</Link>
        </div>
        <h2 style={{ margin: 0 }}>ChatBot</h2>
        <div style={{ fontSize: 12, color: "#666" }}>Ask questions about mine accidents</div>
      </header>

      <main style={styles.main}>
        <section style={styles.left}>
          

          <hr style={{ margin: "20px 0" }} />

          <h3 style={styles.sectionTitle}>Conversation</h3>
          <div style={styles.chatBox}>
            <div style={styles.messages}>
              {messages.length === 0 && <div style={{ color: "#666" }}>No messages yet. Ask a question below.</div>}
              {messages.map((m, i) => (
                <div key={i} style={m.role === "user" ? styles.msgUser : styles.msgBot}>
                  <div style={{ fontSize: 13, whiteSpace: "pre-wrap" }}>{m.text}</div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSendQuestion} style={styles.chatForm}>
              <input
                placeholder="Type your question (e.g. 'How many fatal accidents in 2015?')"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                style={styles.chatInput}
                disabled={loadingQuery}
              />
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <button type="submit" disabled={loadingQuery} style={styles.buttonPrimary}>
                  {loadingQuery ? "Thinking…" : "Send"}
                </button>
              </div>
            </form>
          </div>
        </section>

        {/* <aside style={styles.right}>
          <h4 style={styles.sectionTitle}>Tips</h4>
          <ul>
            <li>Build the index first (use server path to CSV).</li>
            <li>Use short, targeted questions for more accurate retrieval.</li>
            <li>If responses are empty, raise top_k or rebuild index with different chunk size.</li>
            <li>Backend must run at same origin or CORS enabled (app currently allows http://localhost:5173).</li>
          </ul>

          <div style={{ marginTop: 20 }}>
            <h4 style={styles.sectionTitle}>Diagnostics</h4>
            <button style={styles.button} onClick={async () => {
              try {
                const r = await fetch(`${API_BASE || ""}/pinecone_indexes`);
                const j = await r.json();
                alert("Pinecone indexes: " + JSON.stringify(j, null, 2));
              } catch (err) {
                alert("Error: " + err.message);
              }
            }}>List Pinecone Indexes</button>
          </div>
        </aside> */}
      </main>
    </div>
  );
}

const styles = {
  container: { maxWidth: 1200, margin: "20px auto", padding: 16, fontFamily: "Inter, Roboto, sans-serif" },
  header: { display: "flex", gap: 16, alignItems: "center", marginBottom: 12, flexDirection: "column", textAlign: "center" },
  linkBack: { color: "#0366d6", textDecoration: "none", fontSize: 14 },
  main: { display: "flex", gap: 20, alignItems: "flex-start" },
  left: { flex: 1, minWidth: 0, padding: 16, border: "1px solid #eee", borderRadius: 8, background: "#fff" },
  right: { width: 300, padding: 16, border: "1px solid #eee", borderRadius: 8, background: "#fff", height: 520, overflowY: "auto" },
  sectionTitle: { marginBottom: 8 },
  form: { display: "flex", flexDirection: "column", gap: 8 },
  label: { display: "flex", flexDirection: "column", fontSize: 13 },
  input: { padding: "8px 10px", fontSize: 14, marginTop: 6, borderRadius: 6, border: "1px solid #ccc" },
  inputSmall: { width: 80, padding: "6px 8px", fontSize: 14, borderRadius: 6, border: "1px solid #ccc" },
  button: { padding: "8px 12px", borderRadius: 6, border: "1px solid #ccc", background: "#fafafa", cursor: "pointer" },
  buttonPrimary: { padding: "8px 14px", borderRadius: 6, border: "none", background: "#0366d6", color: "#fff", cursor: "pointer" },
  chatBox: { display: "flex", flexDirection: "column", gap: 8 },
  messages: { maxHeight: 300, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, padding: 8, border: "1px dashed #eee", borderRadius: 6, background: "#fafafa" },
  msgUser: { alignSelf: "flex-end", background: "#0366d6", color: "white", padding: 10, borderRadius: 8, maxWidth: "80%" },
  msgBot: { alignSelf: "flex-start", background: "#f1f3f5", color: "#111", padding: 10, borderRadius: 8, maxWidth: "80%" },
  chatForm: { display: "flex", flexDirection: "column", marginTop: 8 },
  chatInput: { padding: "10px", borderRadius: 6, border: "1px solid #ccc", fontSize: 14 }
};
