import React from "react";
import type { Message } from "../types";

const MessagesList: React.FC<{ messages: Message[]; loading: boolean }> = ({ messages, loading }) => (
  <div className="messages">
    {messages.map((msg, i) => (
      <div key={i} className={`message ${msg.role}`}>
        <div className="message-role">{msg.role === "user" ? "You" : "Assistant"}</div>
        <div
          className="message-bubble"
          dangerouslySetInnerHTML={{
            __html: msg.content.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br/>"),
          }}
        />
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
