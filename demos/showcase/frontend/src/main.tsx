import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { loadAnalytics } from "./analytics";
import "./styles.css";

loadAnalytics();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
