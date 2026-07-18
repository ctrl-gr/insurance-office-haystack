import React from "react";
import { SUGGESTIONS } from "../types";

const WelcomeView: React.FC<{ onPick: (s: string) => void }> = ({ onPick }) => (
  <div className="welcome">
    <div className="welcome-icon">🏛</div>
    <h2>How can I help you?</h2>
    <p>Ask for a quote, compare coverages, or find which company best fits your needs.</p>
    <div className="suggestions">
      {SUGGESTIONS.map((s, i) => (
        <button key={i} className="suggestion" onClick={() => onPick(s.replace("→ ", ""))}>
          {s}
        </button>
      ))}
    </div>
  </div>
);

export default WelcomeView;
