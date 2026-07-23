import { useState, useRef, useEffect } from "react";
import "./App.css";
import Header from "./components/Header";
import CompaniesBar from "./components/CompaniesBar";
import WelcomeView from "./components/WelcomeView";
import MessagesList from "./components/MessagesList";
import InputArea from "./components/InputArea";
import type { Message } from "./types";

const API_BASE = "http://localhost:5100";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const adjustTextarea = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  };

  useEffect(() => {
    adjustTextarea();
  }, [input]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", content: text.trim() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    if (textareaRef.current) textareaRef.current.style.height = "auto";

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text.trim(),
          history: messages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          citations: Array.isArray(data.citations) ? data.citations : [],
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "⚠ Connection error. Make sure InsuranceOfficeApi and the Proxy are running.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const onPickSuggestion = (s: string) => sendMessage(s);

  return (
    <div className="app">
      <Header connected={3} />
      <CompaniesBar
        companies={[
          "The Lion Insurance",
          "The Blue Company",
          "The Three Lines",
        ]}
      />

      {messages.length === 0 && !loading ? (
        <WelcomeView onPick={onPickSuggestion} />
      ) : (
        <>
          <MessagesList messages={messages} loading={loading} />
          <div ref={messagesEndRef} />
        </>
      )}

      <InputArea
        input={input}
        setInput={(v) => {
          setInput(v);
          adjustTextarea();
        }}
        sendMessage={sendMessage}
        loading={loading}
        textareaRef={textareaRef}
        handleKeyDown={handleKeyDown}
      />
    </div>
  );
}
