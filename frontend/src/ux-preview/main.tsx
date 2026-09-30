// Separate development entry. Never imported by the production router.
import { mountPreview } from "./App";

if (import.meta.env.DEV) {
  mountPreview();
} else {
  document.getElementById("root")!.textContent =
    "This local design preview is not available in production.";
}
