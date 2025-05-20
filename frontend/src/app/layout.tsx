// app/layout.tsx
import './globals.css'
import { Inter } from 'next/font/google'
import { datasetConfig } from '@/lib/config'
import { Metadata } from 'next'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: datasetConfig.title,
  description: 'Regulatory Comments Analysis',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '32x32' },
      { url: '/favicon.svg', type: 'image/svg+xml' },
    ],
    apple: {
      url: '/apple-touch-icon.png',
      sizes: '180x180',
    },
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.className}>
      <body className="bg-light">
        {children}
      </body>
    </html>
  )
}