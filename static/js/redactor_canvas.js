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
