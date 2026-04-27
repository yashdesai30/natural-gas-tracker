// tailwind.config.js – Tailwind v4 configuration for the dashboard UI
/** @type {import('tailwindcss').Config} */
module.exports = {
  // Scan all files in the src directory for class names
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./app/**/*.{js,ts,jsx,tsx}",
    "./pages/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // You can add custom colors, fonts, etc. here for a premium look
      colors: {
        primary: "hsl(210, 100%, 55%)",
        accent: "hsl(340, 80%, 65%)",
        background: "hsl(210, 10%, 10%)",
        foreground: "hsl(210, 10%, 90%)",
      },
    },
  },
  plugins: [],
};
