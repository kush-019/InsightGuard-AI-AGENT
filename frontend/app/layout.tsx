import type { Metadata } from 'next'; import './globals.css';
export const metadata:Metadata={title:'InsightGuard — AI Anomaly Agent',description:'AI-powered business anomaly detection'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
