'use client';

import styled, { css } from 'styled-components';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'danger' | 'success';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  children: React.ReactNode;
  className?: string;
  title?: string;
  style?: React.CSSProperties;
}

const getButtonColors = (variant: ButtonVariant) => {
  switch (variant) {
    case 'primary':
      return css`
        background-color: #3b82f6;
        color: white;
        border: 1px solid #3b82f6;
        &:hover:not(:disabled) {
          background-color: #2563eb;
          border-color: #2563eb;
        }
      `;
    case 'secondary':
      return css`
        background-color: #64748b;
        color: white;
        border: 1px solid #64748b;
        &:hover:not(:disabled) {
          background-color: #475569;
          border-color: #475569;
        }
      `;
    case 'outline':
      return css`
        background-color: transparent;
        color: #3b82f6;
        border: 1px solid #3b82f6;
        &:hover:not(:disabled) {
          background-color: rgba(59, 130, 246, 0.1);
        }
      `;
    case 'danger':
      return css`
        background-color: #ef4444;
        color: white;
        border: 1px solid #ef4444;
        &:hover:not(:disabled) {
          background-color: #dc2626;
          border-color: #dc2626;
        }
      `;
    case 'success':
      return css`
        background-color: #10b981;
        color: white;
        border: 1px solid #10b981;
        &:hover:not(:disabled) {
          background-color: #059669;
          border-color: #059669;
        }
      `;
    default:
      return css`
        background-color: #3b82f6;
        color: white;
        border: 1px solid #3b82f6;
        &:hover:not(:disabled) {
          background-color: #2563eb;
          border-color: #2563eb;
        }
      `;
  }
};

const getButtonSize = (size: ButtonSize) => {
  switch (size) {
    case 'sm':
      return css`
        padding: 0.375rem 0.75rem;
        font-size: 0.875rem;
      `;
    case 'md':
      return css`
        padding: 0.5rem 1rem;
        font-size: 1rem;
      `;
    case 'lg':
      return css`
        padding: 0.75rem 1.5rem;
        font-size: 1.125rem;
      `;
    default:
      return css`
        padding: 0.5rem 1rem;
        font-size: 1rem;
      `;
  }
};

const StyledButton = styled.button<{ variant: ButtonVariant; size: ButtonSize; $disabled: boolean }>`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
  border-radius: 0.375rem;
  transition: all 0.15s ease-in-out;
  cursor: ${(props) => (props.$disabled ? 'not-allowed' : 'pointer')};
  opacity: ${(props) => (props.$disabled ? 0.65 : 1)};
  ${(props) => getButtonColors(props.variant)}
  ${(props) => getButtonSize(props.size)}

  &:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
  }

  &:disabled {
    background-color: #e2e8f0;
    color: #64748b;
    border-color: #e2e8f0;
    cursor: not-allowed;
  }
`;

export default function Button({
  variant = 'primary',
  size = 'md',
  onClick,
  disabled = false,
  type = 'button',
  children,
  className,
  title,
  style
}: ButtonProps) {
  return (
    <StyledButton
      variant={variant}
      size={size}
      onClick={onClick}
      disabled={disabled}
      $disabled={disabled}
      type={type}
      className={className}
      title={title}
      style={style}
    >
      {children}
    </StyledButton>
  );
} 