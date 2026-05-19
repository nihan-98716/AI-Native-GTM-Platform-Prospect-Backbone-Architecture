import '../styles/globals.css'
import Providers from '../components/layout/Providers'
import Layout from '../components/layout/Layout'

export const metadata = {
  title: 'Prospect UI',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <Layout>{children}</Layout>
        </Providers>
      </body>
    </html>
  )
}
