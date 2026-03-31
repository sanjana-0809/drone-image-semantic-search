import './globals.css';

export const metadata = {
  title: 'Drone Search Engine — Skylark Drones',
  description: 'AI-powered semantic search through aerial drone imagery using natural language queries',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-surface-900 text-white antialiased">
        {children}
      </body>
    </html>
  );
}
