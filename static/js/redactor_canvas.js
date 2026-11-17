(function () {
  class RedactorCanvas {
    constructor(canvas, infoEl) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.infoEl = infoEl;
      this.pdfFile = null;
      this.pageIndex = 0;
      this.pageCount = 0;
      this.pageImage = new Image();
      this.boxes = []; // {page, x0,y0,x1,y1} normalized 0..1
      this.drawing = false;
      this.start = null;
      this.current = null;
      this._bindEvents();
    }

    _bindEvents() {
      this.canvas.addEventListener('mousedown', (e) => this.onDown(e));
      this.canvas.addEventListener('mousemove', (e) => this.onMove(e));
      window.addEventListener('mouseup', (e) => this.onUp(e));
      this.canvas.addEventListener('mouseleave', () => { if (this.drawing) this.cancelDraw(); });
    }

    reset() {
      this.pdfFile = null;
      this.pageIndex = 0;
      this.pageCount = 0;
      this.boxes = [];
      this.pageImage = new Image();
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.canvas.width = 0; this.canvas.height = 0;
      this.updateInfo();
    }

    async setPdfFile(file) {
      this.reset();
      this.pdfFile = file;
      // probe page count by loading page 0 and reading errors is not enough; we infer by trying sequentially? easier: request pages until error
      // but better: get page count via a lightweight approach: try loading page 0 and increment; we'll detect on demand.
      this.pageCount = await this.detectPageCount(file);
      if (this.pageCount <= 0) throw new Error('Could not read PDF pages.');
      await this.loadPage(0);
    }

    async detectPageCount(file) {
      // Binary search/count by probing; to keep simple and local, try up to a reasonable cap by probing sequentially with early stop.
      // We'll attempt to fetch pages in steps: 0,1,2,... until failure.
      // Optimize: exponential then binary.
      let lo = 0, hi = 1;
      // find upper bound
      while (await this.pageExists(file, hi)) {
        lo = hi;
        hi *= 2;
        if (hi > 5000) break; // safety cap
      }
      // binary search between lo (exists) and hi (not exists)
      let left = lo, right = hi;
      while (left + 1 < right) {
        const mid = Math.floor((left + right) / 2);
        if (await this.pageExists(file, mid)) left = mid; else right = mid;
      }
      return left + 1;
    }

    async pageExists(file, page) {
      try {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('page', String(page));
        const res = await fetch('/api/redact/preview', { method: 'POST', body: fd });
        if (!res.ok) return false;
        // consume small blob
        await res.blob();
        return true;
      } catch (_) {
        return false;
      }
    }

    async loadPage(index) {
      if (!this.pdfFile) return;
      if (index < 0 || index >= this.pageCount) return;
      const fd = new FormData();
      fd.append('file', this.pdfFile);
      fd.append('page', String(index));
      const res = await fetch('/api/redact/preview', { method: 'POST', body: fd });
      if (!res.ok) {
        let msg = 'Failed to render page preview.';
        try { const j = await res.json(); msg = j.error || j.detail || msg; } catch (_) {}
        throw new Error(msg);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      await new Promise((resolve, reject) => {
        this.pageImage = new Image();
        this.pageImage.onload = () => { URL.revokeObjectURL(url); resolve(); };
        this.pageImage.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Failed to load page image.')); };
        this.pageImage.src = url;
      });
      this.pageIndex = index;
      this.canvas.width = this.pageImage.naturalWidth;
      this.canvas.height = this.pageImage.naturalHeight;
      this.render();
      this.updateInfo();
    }

    updateInfo() {
      if (this.infoEl) {
        const total = this.pageCount || 0;
        const current = total ? (this.pageIndex + 1) : 0;
        this.infoEl.textContent = `Page ${current} / ${total}`;
      }
    }

    getMousePos(evt) {
      const rect = this.canvas.getBoundingClientRect();
      const scaleX = this.canvas.width / rect.width;
      const scaleY = this.canvas.height / rect.height;
      return {
        x: (evt.clientX - rect.left) * scaleX,
        y: (evt.clientY - rect.top) * scaleY,
      };
    }

    onDown(evt) {
      if (!this.pdfFile || !this.canvas.width) return;
      evt.preventDefault();
      this.drawing = true;
      this.start = this.getMousePos(evt);
      this.current = this.start;
    }

    onMove(evt) {
      if (!this.drawing) return;
      this.current = this.getMousePos(evt);
      this.render();
      this.drawRect(this.start, this.current, true);
    }

    onUp(evt) {
      if (!this.drawing) return;
      const end = this.current || this.getMousePos(evt);
      this.drawing = false;
      const box = this.normalizeBox(this.start, end);
      this.start = null; this.current = null;
      if (box) {
        this.boxes.push({ page: this.pageIndex, ...box });
      }
      this.render();
