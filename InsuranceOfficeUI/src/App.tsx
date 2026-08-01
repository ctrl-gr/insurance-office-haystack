import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import CompaniesBar from "./components/CompaniesBar";
import ConversationSidebar from "./components/ConversationSidebar";
import Header from "./components/Header";
import InputArea from "./components/InputArea";
import MessagesList from "./components/MessagesList";
import WelcomeView from "./components/WelcomeView";
import type { Conversation, Message } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5100";
const SESSION_STORAGE_KEY = "insurance-office.session-id";

const normalizeMessages = (messages: Message[]) =>
  messages.map((message) => ({
    role: message.role,
    content: message.content,
    citations: message.citations ?? [],
  }));

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const initializedRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const refreshConversations = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/sessions`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const next = Array.isArray(payload.sessions) ? payload.sessions : [];
    setConversations(next);
    return next as Conversation[];
  }, []);

  const createSession = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/sessions`, { method: "POST" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const session = (await response.json()) as Conversation;
    localStorage.setItem(SESSION_STORAGE_KEY, session.sessionId);
    setSessionId(session.sessionId);
    setMessages([]);
    setConversations((previous) => [
      session,
      ...previous.filter((item) => item.sessionId !== session.sessionId),
    ]);
    return session.sessionId;
  }, []);

  const loadSession = useCallback(async (nextSessionId: string) => {
    setInitializing(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/sessions/${nextSessionId}/messages`,
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      localStorage.setItem(SESSION_STORAGE_KEY, nextSessionId);
      setSessionId(nextSessionId);
      setMessages(normalizeMessages(payload.messages));
      setSidebarOpen(false);
    } finally {
      setInitializing(false);
    }
  }, []);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    const restoreSession = async () => {
      try {
        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
        await refreshConversations();
        if (!storedSessionId) {
          await createSession();
          return;
        }
        try {
          await loadSession(storedSessionId);
        } catch {
          localStorage.removeItem(SESSION_STORAGE_KEY);
          await createSession();
        }
      } catch {
        setMessages([
          {
            role: "assistant",
            content: "Connection error. Make sure the backend and MongoDB are available.",
          },
        ]);
      } finally {
        setInitializing(false);
      }
    };

    void restoreSession();
  }, [createSession, loadSession, refreshConversations]);

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
          citations: Array.isArray(payload.citations) ? payload.citations : [],
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
      void refreshConversations().catch(() => undefined);
    }
  };

  const startConversation = async () => {
    if (loading || initializing) return;
    setInitializing(true);
    try {
      await createSession();
      setSidebarOpen(false);
    } finally {
      setInitializing(false);
    }
  };

  const deleteConversation = async (targetSessionId: string) => {
    const conversation = conversations.find(
      (item) => item.sessionId === targetSessionId,
    );
    if (!window.confirm(`Delete "${conversation?.title ?? "this conversation"}"?`)) {
      return;
    }

    setInitializing(true);
    try {
      const response = await fetch(`${API_BASE}/api/sessions/${targetSessionId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setConversations((previous) =>
        previous.filter((item) => item.sessionId !== targetSessionId),
      );
      if (targetSessionId === sessionId) await createSession();
    } finally {
      setInitializing(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage(input);
    }
  };

  const isBusy = loading || initializing;

  return (
    <div className="app-shell">
      <ConversationSidebar
        conversations={conversations}
        activeSessionId={sessionId}
        open={sidebarOpen}
        loading={isBusy}
        onClose={() => setSidebarOpen(false)}
        onCreate={() => void startConversation()}
        onSelect={(nextSessionId) => {
          if (nextSessionId !== sessionId) void loadSession(nextSessionId);
          else setSidebarOpen(false);
        }}
        onDelete={(targetSessionId) => void deleteConversation(targetSessionId)}
      />

      <main className="app">
        <Header connected={3} onOpenSidebar={() => setSidebarOpen(true)} />
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
            <MessagesList
              messages={messages}
              loading={isBusy}
              endRef={messagesEndRef}
            />
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
      </main>
    </div>
  );
}
