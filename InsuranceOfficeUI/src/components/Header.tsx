import React from "react";

export const Header: React.FC<{ connected: number }> = ({ connected }) => (
  <header className="header">
    <div className="header-left">
      <h1>Insurance Office</h1>
      <div className="tagline">Multi-Company Assistant</div>
    </div>
    <div className="status-row">
      <div className="status-dot" />
      <span>{connected} companies connected</span>
    </div>
  </header>
);

export default Header;
