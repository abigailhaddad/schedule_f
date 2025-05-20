'use client';

import styled from 'styled-components';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
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

const StyledCard = styled.div`
  background-color: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  overflow: hidden;
  transition: box-shadow 0.2s ease-in-out;
  margin-bottom: 1.5rem;
  border: 1px solid rgba(0, 0, 0, 0.05);
  
  &:hover {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
`;

const StyledCardHeader = styled.div`
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  background-color: rgba(0, 0, 0, 0.01);
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const StyledCardBody = styled.div<{ $noPadding?: boolean }>`
  padding: ${props => props.$noPadding ? '0' : '1.25rem'};
`;

const StyledCardFooter = styled.div`
  padding: 1rem 1.25rem;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  background-color: rgba(0, 0, 0, 0.01);
`;

function Card({ children, className }: CardProps) {
  return <StyledCard className={className}>{children}</StyledCard>;
}

function CardHeader({ children, className }: CardHeaderProps) {
  return <StyledCardHeader className={className}>{children}</StyledCardHeader>;
}

function CardBody({ children, className, noPadding }: CardBodyProps) {
  return <StyledCardBody className={className} $noPadding={noPadding}>{children}</StyledCardBody>;
}

function CardFooter({ children, className }: CardFooterProps) {
  return <StyledCardFooter className={className}>{children}</StyledCardFooter>;
}

Card.Header = CardHeader;
Card.Body = CardBody;
Card.Footer = CardFooter;

export default Card; 