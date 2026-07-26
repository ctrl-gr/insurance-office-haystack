import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import Header from "./components/Header";
import CompaniesBar from "./components/CompaniesBar";
import WelcomeView from "./components/WelcomeView";
import MessagesList from "./components/MessagesList";
import InputArea from "./components/InputArea";
import type { Message } from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5100";
const SESSION_STORAGE_KEY = "insurance-office.session-id";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const initializedRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const createSession = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/sessions`, {
      method: "POST",
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const session = await response.json();
    localStorage.setItem(SESSION_STORAGE_KEY, session.sessionId);
    setSessionId(session.sessionId);
    setMessages([]);
    return session.sessionId as string;
  }, []);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    const restoreSession = async () => {
      try {
        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
        if (!storedSessionId) {
          await createSession();
          return;
        }
        const response = await fetch(
          `${API_BASE}/api/sessions/${storedSessionId}/messages`,
        );
        if (response.status === 404) {
          localStorage.removeItem(SESSION_STORAGE_KEY);
          await createSession();
          return;
        }
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        setSessionId(storedSessionId);
        setMessages(
          payload.messages.map((message: Message) => ({
            role: message.role,
            content: message.content,
            citations: message.citations ?? [],
          })),
        );
      } catch {
        setMessages([
          {
            role: "assistant",
            content:
              "Connection error. Make sure the backend and MongoDB are available.",
          },
        ]);
      } finally {
        setInitializing(false);
      }
    };

    void restoreSession();
  }, [createSession]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const adjustTextarea = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
  };

  useEffect(() => {
    adjustTextarea();
  }, [input]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading || initializing || !sessionId) return;

    const userMessage: Message = { role: "user", content: text.trim() };
    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setLoading(true);

    if (textareaRef.current) textareaRef.current.style.height = "auto";

    try {
      const response = await fetch(
        `${API_BASE}/api/sessions/${sessionId}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text.trim() }),
        },
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const payload = await response.json();
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: payload.reply,
          citations: Array.isArray(payload.citations)
            ? payload.citations
            : [],
        },
      ]);
    } catch {
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            "Connection error. Make sure the backend, proxy, and MongoDB are running.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage(input);
    }
  };

  const isBusy = loading || initializing;

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

      {messages.length === 0 && !isBusy ? (
        <WelcomeView onPick={(suggestion) => void sendMessage(suggestion)} />
      ) : (
        <>
          <MessagesList messages={messages} loading={isBusy} />
          <div ref={messagesEndRef} />
        </>
      )}

      <InputArea
        input={input}
        setInput={(value) => {
          setInput(value);
          adjustTextarea();
        }}
        sendMessage={sendMessage}
        loading={isBusy}
        textareaRef={textareaRef}
        handleKeyDown={handleKeyDown}
      />
    </div>
  );
}
