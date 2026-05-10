import "./globals.css";

export const metadata = { title: "Avrovo", description: "Family healthcare monitoring" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
