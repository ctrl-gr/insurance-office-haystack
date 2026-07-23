import React from "react";
import type { Citation, Message } from "../types";

const renderSafeText = (content: string) =>
  content.split("\n").map((line, lineIndex) => (
    <React.Fragment key={lineIndex}>
      {line.split(/(\*\*.*?\*\*)/g).map((part, partIndex) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={partIndex}>{part.slice(2, -2)}</strong>
        ) : (
          <React.Fragment key={partIndex}>{part}</React.Fragment>
        ),
      )}
      {lineIndex < content.split("\n").length - 1 && <br />}
    </React.Fragment>
  ));

const safeHttpUrl = (value?: string | null) => {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : null;
  } catch {
    return null;
  }
};

const CitationLink: React.FC<{ citation: Citation }> = ({ citation }) => {
  const url = safeHttpUrl(citation.url);
  const label = `${citation.policyName} · page ${citation.pageNumber}`;
  return url ? (
    <a className="citation-link" href={url} target="_blank" rel="noreferrer">
      <span>{label}</span>
      <span aria-hidden="true">↗</span>
    </a>
  ) : (
    <span className="citation-link citation-link-disabled">{label}</span>
  );
};

const MessagesList: React.FC<{ messages: Message[]; loading: boolean }> = ({ messages, loading }) => (
  <div className="messages">
    {messages.map((msg, i) => (
      <div key={i} className={`message ${msg.role}`}>
        <div className="message-role">{msg.role === "user" ? "You" : "Assistant"}</div>
        <div className="message-bubble">{renderSafeText(msg.content)}</div>
        {msg.role === "assistant" && Boolean(msg.citations?.length) && (
          <div className="message-citations" aria-label="Sources">
            <div className="citations-title">Sources</div>
            {msg.citations?.map((citation) => (
              <CitationLink key={citation.source} citation={citation} />
            ))}
          </div>
        )}
      </div>
    ))}

    {loading && (
      <div className="message assistant">
        <div className="message-role">Assistant</div>
        <div className="thinking">
          <div className="thinking-dots">
            <span />
            <span />
            <span />
          </div>
          Consulting companies...
        </div>
      </div>
    )}
  </div>
);

export default MessagesList;
