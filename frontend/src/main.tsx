import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { installSessionFetch } from "./api/client.ts";
import "./index.css";
import App from "./App.tsx";

installSessionFetch();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
