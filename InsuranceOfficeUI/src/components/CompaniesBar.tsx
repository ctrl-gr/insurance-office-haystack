import React from "react";

const CompaniesBar: React.FC<{ companies: string[] }> = ({ companies }) => (
  <div className="companies-bar">
    {companies.map((c) => (
      <span className="company-pill" key={c}>
        {c}
      </span>
    ))}
  </div>
);

export default CompaniesBar;
