# VaultPDF Studio (Local PDF Utility Studio)

**VaultPDF Studio** is a complete, 100% offline, privacy-first PDF toolkit that runs locally on your machine. It is a zero-upload alternative to cloud PDF services: files are processed in isolated temporary workspaces on disk and automatically deleted immediately after each download/response.

Built with **Python FastAPI** and a **Light Neo-Brutalism** frontend (no glassmorphism, no blur effects, no dark mode gradients).

## 🔗 Live Demo

**Try it now: [https://stanford-cam-tap-joining.trycloudflare.com](https://stanford-cam-tap-joining.trycloudflare.com)**

> The live demo is served from the developer's machine through a temporary Cloudflare tunnel, so it may be unavailable at times. For a permanent HTTPS deployment, follow [`DEPLOY_SELF_HOST.md`](DEPLOY_SELF_HOST.md).

## Privacy Architecture

- **100% offline processing:** All PDF operations run locally on your computer. No files are uploaded to any third-party server.
- **Zero uploads:** The browser talks only to your local FastAPI server (`localhost`).
- **Isolated per-request workspaces:** Every API request creates a unique workspace inside `.temp_workspace/`.
- **Automatic cleanup:** Uploaded inputs and generated outputs are scheduled for deletion via FastAPI `BackgroundTasks` immediately after the response/download completes (best-effort cleanup on errors as well).
