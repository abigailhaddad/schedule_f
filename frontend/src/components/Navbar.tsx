// components/Navbar.tsx
"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { datasetConfig } from "@/lib/config";
import Image from "next/image";

export default function Navbar() {
  const { title, subtitle, description } = datasetConfig;
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // Handle scroll effect
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Toggle menu and handle keyboard navigation
  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  // Handle keyboard events for menu button
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape" && isMenuOpen) {
      setIsMenuOpen(false);
    }
  };

  return (
    <div className="relative">
      {/* Desktop Beta Badge - diagonal in top-right corner */}
      <div className="absolute right-0 top-0 z-50 overflow-hidden w-28 h-28 pointer-events-none hidden sm:block">
        <div className="absolute top-8 right-[-35px] rotate-45 w-[170px] text-center">
          <div className="bg-yellow-700 text-white font-bold py-1 text-xs shadow-md">
            BETA
          </div>
        </div>
      </div>
      
      {/* Mobile Beta Badge - simple horizontal badge */}
      <div className="absolute left-3 top-2 z-50 pointer-events-none sm:hidden">
        <div className="bg-yellow-700 text-white font-bold text-xs py-0.5 px-2 rounded shadow-sm">
          BETA
        </div>
      </div>
      
      <nav
        className={`fixed top-0 left-0 right-0 z-40 transition-all duration-300 ${
          scrolled
            ? "bg-primary/95 backdrop-blur-sm shadow-lg py-2"
            : "bg-primary shadow-md py-3"
        } text-white`}
        aria-label="Main navigation"
      >
        <div className="container mx-auto px-4">
          <div className="flex justify-between items-center">
            {/* Logo & Title */}
            <div className="flex items-center space-x-3">
              <div
                className={`transition-transform duration-300 ${
                  scrolled ? "scale-90" : "scale-100"
                }`}
              >
                <Image
                  src="/favicon.svg"
                  alt="Schedule F Logo"
                  width={28}
                  height={28}
                  className="w-7 h-7"
                />
              </div>
              <div className="flex flex-col">
                <Link
                  href="/"
                  className={`navbar-brand-text font-bold hover:text-white/80 transition-all duration-300 ${
                    scrolled ? "text-lg md:text-xl" : "text-xl md:text-2xl"
                  }`}
                  aria-label={`${title} - Home`}
                >
                  {title}
                </Link>
                <a
                  href="https://www.regulations.gov/document/OPM-2025-0004-0001"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`group text-xs md:text-sm text-white/90 hover:text-white max-w-sm md:max-w-xl lg:max-w-2xl transition-all duration-300 flex items-center ${
                    scrolled ? "hidden md:flex" : "flex"
                  }`}
                  aria-label="View official regulations document (opens in new tab)"
                >
                  <span>
                    {description}
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-3 w-3 ml-0.5 opacity-70 group-hover:opacity-100 transition-opacity inline-flex"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                      />
                    </svg>
                  </span>
                </a>
              </div>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center">
              {subtitle && (
                <Link
                  href="https://github.com/your-repo"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center bg-white/20 px-3 py-1.5 rounded hover:bg-white/30 transition-colors"
                  aria-label="GitHub repository (opens in new tab)"
                >
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                    aria-hidden="true"
                  >
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                  </svg>
                  {subtitle}
                </Link>
              )}
            </div>
            
            {/* Mobile Menu Button - Only show if we have a subtitle */}
            {subtitle && (
              <button
                className="md:hidden flex items-center"
                onClick={toggleMenu}
                onKeyDown={handleKeyDown}
                aria-expanded={isMenuOpen}
                aria-label="Toggle navigation menu"
                aria-controls="mobile-menu"
              >
                <span className="sr-only">Open menu</span>
                <div className="w-6 flex flex-col gap-1.5">
                  <span
                    className={`block h-0.5 w-full bg-white transform transition-transform duration-300 ease-in-out ${
                      isMenuOpen ? "rotate-45 translate-y-2" : ""
                    }`}
                  ></span>
                  <span
                    className={`block h-0.5 w-full bg-white transition-opacity duration-300 ease-in-out ${
                      isMenuOpen ? "opacity-0" : "opacity-100"
                    }`}
                  ></span>
                  <span
                    className={`block h-0.5 w-full bg-white transform transition-transform duration-300 ease-in-out ${
                      isMenuOpen ? "-rotate-45 -translate-y-2" : ""
                    }`}
                  ></span>
                </div>
              </button>
            )}
          </div>
          
          {/* Mobile Navigation - Only show if we have a subtitle */}
          {subtitle && (
            <div
              id="mobile-menu"
              className={`md:hidden overflow-hidden transition-all duration-300 ease-in-out ${
                isMenuOpen
                  ? "max-h-64 opacity-100 py-4"
                  : "max-h-0 opacity-0 py-0"
              }`}
              aria-hidden={!isMenuOpen}
            >
              <div className="flex flex-col space-y-3">
                <Link
                  href="https://github.com/your-repo"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center py-2 px-3 rounded-md hover:bg-white/10 transition-colors"
                  onClick={() => setIsMenuOpen(false)}
                  aria-label="GitHub repository (opens in new tab)"
                  tabIndex={isMenuOpen ? 0 : -1}
                >
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                    aria-hidden="true"
                  >
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                  </svg>
                  GitHub Repo
                </Link>
              </div>
            </div>
          )}
        </div>
      </nav>
    </div>
  );
}
