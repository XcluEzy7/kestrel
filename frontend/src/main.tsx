import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { installSessionFetch } from "./api/client.ts";
import "./index.css";
import App from "./App.tsx";

installSessionFetch();

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js");
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
