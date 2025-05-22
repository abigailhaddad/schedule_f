'use client';

import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  role?: string;
  ariaLabel?: string;
}

interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
  id?: string;
}

interface CardBodyProps {
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
}

interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
}

function Card({ children, className = '', role, ariaLabel }: CardProps) {
  return (
    <section 
      className={`card shadow-md mb-6 ${className}`}
      role={role}
      aria-label={ariaLabel}
    >
      {children}
    </section>
  );
}

function CardHeader({ children, className = '', id }: CardHeaderProps) {
  return (
    <header 
      className={`card-header ${className}`}
      id={id}
    >
      {children}
    </header>
  );
}

function CardBody({ children, className = '', noPadding = false }: CardBodyProps) {
  return (
    <div className={`card-body ${noPadding ? 'p-0' : ''} ${className}`}>
      {children}
    </div>
  );
}

function CardFooter({ children, className = '' }: CardFooterProps) {
  return (
    <footer className={`card-footer ${className}`}>
      {children}
    </footer>
  );
}

Card.Header = CardHeader;
Card.Body = CardBody;
Card.Footer = CardFooter;

export default Card; 