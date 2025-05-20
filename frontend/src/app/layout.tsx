// app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { datasetConfig } from '@/lib/config';
import StyledComponentsRegistry from '@/components/registry';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: datasetConfig.title,
  description: 'Regulatory Comments Analysis',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <StyledComponentsRegistry>
          {children}
        </StyledComponentsRegistry>
      </body>
    </html>
  );
}