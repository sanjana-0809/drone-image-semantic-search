import './globals.css';

export const metadata = {
  title: 'Drone Search Engine - Skylark Drones',
  description: 'AI-powered semantic search through aerial drone imagery using natural language queries',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-surface-900 text-white antialiased">
        {children}
      </body>
    </html>
  );
}
