import React from "react";

const InputArea: React.FC<{
  input: string;
  setInput: (v: string) => void;
  sendMessage: (t: string) => Promise<void>;
  loading: boolean;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}> = ({
  input,
  setInput,
  sendMessage,
  loading,
  textareaRef,
  handleKeyDown,
}) => {
  return (
    <div className="input-area">
      <div className="input-row">
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Write a message..."
            rows={1}
            disabled={loading}
          />
        </div>
        <button
          className="send-btn"
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || loading}
          title="Send (Enter)"
        >
          ↑
        </button>
      </div>
      <div className="input-hint">Enter to send · Shift+Enter for newline</div>
    </div>
  );
};

export default InputArea;
