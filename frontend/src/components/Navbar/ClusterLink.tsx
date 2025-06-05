import Link from "next/link";
import React from "react";

type ClusterLinkProps = {
  className?: string;
  onClick?: () => void;
  tabIndex?: number;
};

const ClusterLink: React.FC<ClusterLinkProps> = ({ className = "", onClick, tabIndex }) => (
  <Link
    href="/clusters"
    className={`flex items-center bg-slate-100 text-slate-700 px-3 py-1.5 rounded hover:bg-slate-200 transition-colors border border-slate-200 ${className}`}
    onClick={onClick}
    tabIndex={tabIndex}
    aria-label="View clusters page"
  >
    {/* Cluster icon (grid/network) */}
    <svg
      className="w-5 h-5 mr-2"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <circle cx="5" cy="5" r="2" />
      <circle cx="19" cy="5" r="2" />
      <circle cx="5" cy="19" r="2" />
      <circle cx="19" cy="19" r="2" />
      <line x1="5" y1="5" x2="19" y2="5" />
      <line x1="5" y1="19" x2="19" y2="19" />
      <line x1="5" y1="5" x2="5" y2="19" />
      <line x1="19" y1="5" x2="19" y2="19" />
    </svg>
    Clusters
  </Link>
);

export default ClusterLink; 