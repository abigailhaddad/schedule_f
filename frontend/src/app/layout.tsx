// app/layout.tsx
import './globals.css'
import { Inter } from 'next/font/google'
import { datasetConfig } from '@/lib/config'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: datasetConfig.title,
  description: 'Regulatory Comments Analysis',
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