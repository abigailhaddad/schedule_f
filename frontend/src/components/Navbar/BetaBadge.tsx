import React from "react";

const BetaBadge = () => (
  <>
    {/* Desktop Beta Badge - diagonal in top-right corner, hidden on mobile */}
    <div className="absolute right-0 top-0 z-50 overflow-hidden w-28 h-28 pointer-events-none hidden md:block">
      <div className="absolute top-8 right-[-35px] rotate-45 w-[170px] text-center">
        <div className="bg-yellow-700 text-white font-bold py-1 text-xs shadow-md">
          BETA
        </div>
      </div>
    </div>
    {/* Mobile Beta Badge - simple horizontal badge in top right */}
    <div className="absolute right-3 top-2 z-50 pointer-events-none md:hidden">
      <div className="bg-yellow-700 text-white font-bold text-xs py-0.5 px-2 rounded shadow-sm">
        BETA
      </div>
    </div>
  </>
);

export default BetaBadge; 