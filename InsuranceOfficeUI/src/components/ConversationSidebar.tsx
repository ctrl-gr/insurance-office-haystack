import type { Conversation } from "../types";

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeSessionId: string | null;
  open: boolean;
  loading: boolean;
  onClose: () => void;
  onCreate: () => void;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
}

const formatDate = (value: string) => {
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
};

export default function ConversationSidebar({
  conversations,
  activeSessionId,
  open,
  loading,
  onClose,
  onCreate,
  onSelect,
  onDelete,
}: ConversationSidebarProps) {
  return (
    <>
      <aside className={`conversation-sidebar${open ? " open" : ""}`} aria-label="Past conversations">
        <div className="sidebar-header">
          <div>
            <div className="sidebar-eyebrow">Insurance Office</div>
            <h2>Conversations</h2>
          </div>
          <button className="sidebar-close" onClick={onClose} aria-label="Close conversations">
            x
          </button>
        </div>

        <button className="new-conversation" onClick={onCreate} disabled={loading}>
          <span aria-hidden="true">+</span>
          New conversation
        </button>

        <div className="conversation-list">
          {conversations.length === 0 && !loading ? (
            <p className="conversation-empty">Your past conversations will appear here.</p>
          ) : (
            conversations.map((conversation) => (
              <div
                className={`conversation-item${conversation.sessionId === activeSessionId ? " active" : ""}`}
                key={conversation.sessionId}
              >
                <button
                  className="conversation-select"
                  onClick={() => onSelect(conversation.sessionId)}
                  disabled={loading}
                  aria-current={conversation.sessionId === activeSessionId ? "page" : undefined}
                >
                  <span className="conversation-title">{conversation.title}</span>
                  <span className="conversation-meta">
                    {formatDate(conversation.updatedAt)}
                    {conversation.messageCount > 0 ? ` / ${conversation.messageCount} messages` : ""}
                  </span>
                </button>
                <button
                  className="conversation-delete"
                  onClick={() => onDelete(conversation.sessionId)}
                  disabled={loading}
                  aria-label={`Delete ${conversation.title}`}
                  title="Delete conversation"
                >
                  x
                </button>
              </div>
            ))
          )}
        </div>
      </aside>
      {open && <button className="sidebar-backdrop" onClick={onClose} aria-label="Close conversations" />}
    </>
  );
}
