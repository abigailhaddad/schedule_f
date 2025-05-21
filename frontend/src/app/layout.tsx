// app/layout.tsx
import './globals.css'
import { datasetConfig } from '@/lib/config'
import { Metadata } from 'next'

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
    <html lang="en">
      <body className="bg-light font-sans">
        {children}
      </body>
    </html>
  )
}