(function () {
  const $ = (sel) => document.querySelector(sel);
  const toolGrid = $('#tool-grid');
  const toolHeading = $('#tool-heading');
  const toolDescription = $('#tool-description');
  const dropZone = $('#drop-zone');
  const dropTitle = $('#drop-title');
  const dropSubtitle = $('#drop-subtitle');
  const fileInput = $('#file-input');
  const fileListEl = $('#file-list');
  const reorderHint = $('#reorder-hint');
  const optionsEl = $('#options');
  const actionsEl = $('#actions');
  const banner = $('#banner');
  const loading = $('#loading');
  const loadingText = $('#loading-text');
  const redactArea = $('#redact-area');
  const redactCanvasEl = $('#redact-canvas');
  const redactPageInfo = $('#redact-page-info');

  const state = {
    tool: 'merge',
    files: [], // File[]
    redact: null,
  };

  const TOOLS = {
    'merge': {
      title: 'Merge PDFs',
      desc: 'Combine multiple PDFs in the specified order.',
      accept: '.pdf,application/pdf',
      multiple: true,
      reorder: true,
      minFiles: 2,
      action: { label: 'Merge & Download', endpoint: '/api/merge' },
      options: () => ''
    },
    'split': {
      title: 'Split PDF',
      desc: 'Extract page ranges like "1-3, 5, 7-9" (1-indexed) into a ZIP of PDFs.',
      accept: '.pdf,application/pdf',
      multiple: false,
      minFiles: 1,
      action: { label: 'Split & Download ZIP', endpoint: '/api/split' },
      options: () => `
        <div class="field">
          <label for="ranges">Page ranges</label>
          <input type="text" id="ranges" placeholder="e.g. 1-3, 5, 7-9" />
        </div>`
    },
    'compress': {
      title: 'Compress to Target KB',
      desc: 'Iteratively downscale images and quality to reach your target size.',
      accept: '.pdf,application/pdf',
      multiple: false,
      minFiles: 1,
      action: { label: 'Compress & Download', endpoint: '/api/compress' },
      options: () => `
        <div class="field">
          <label for="target_kb">Target size (KB)</label>
          <input type="number" id="target_kb" min="1" step="1" placeholder="e.g. 1500" />
        </div>`
    },
    'redact': {
      title: 'True Redact',
      desc: 'Draw boxes to permanently remove underlying text and image data.',
      accept: '.pdf,application/pdf',
      multiple: false,
      minFiles: 1,
      action: { label: 'Permanently Redact & Download', endpoint: '/api/redact/apply' },
      options: () => ''
    },
    'convert-pdf-word': {
      title: 'PDF ↔ Word',
      desc: 'Convert PDF to DOCX, or DOCX to PDF (Word to PDF requires Microsoft Word on Windows).',
      accept: '.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      multiple: false,
      minFiles: 1,
      action: null, // dynamic
      options: () => `
        <div class="field">
          <label for="convert_mode">Conversion</label>
          <select id="convert_mode">
            <option value="pdf-to-word">PDF → Word (.docx)</option>
            <option value="word-to-pdf">Word (.docx) → PDF (Windows)</option>
          </select>
        </div>`
    },
    'convert-pdf-images': {
      title: 'PDF ↔ Images',
      desc: 'Export PDF pages as images, or bundle images into a single PDF.',
      accept: '.pdf,.png,.jpg,.jpeg,image/png,image/jpeg,application/pdf',
      multiple: true,
      reorder: true,
      minFiles: 1,
      action: null, // dynamic
      options: () => `
        <div class="field inline">
          <div class="field">
            <label for="img_mode">Mode</label>
            <select id="img_mode">
              <option value="pdf-to-images">PDF → Images (ZIP)</option>
              <option value="images-to-pdf">Images → PDF</option>
            </select>
          </div>
          <div class="field" id="img_fmt_wrap">
            <label for="img_fmt">Image format</label>
            <select id="img_fmt">
              <option value="png">PNG</option>
              <option value="jpg">JPG</option>
            </select>
          </div>
          <div class="field" id="img_dpi_wrap">
            <label for="img_dpi">DPI</label>
            <input type="number" id="img_dpi" value="150" min="36" max="600" step="1" />
          </div>
        </div>`
    },
    'protect-unlock': {
      title: 'Protect / Unlock',
      desc: 'Encrypt with AES-256 or decrypt a password-protected PDF.',
      accept: '.pdf,application/pdf',
      multiple: false,
      minFiles: 1,
      action: null, // dynamic
      options: () => `
        <div class="field inline">
          <div class="field">
            <label for="lock_mode">Mode</label>
            <select id="lock_mode">
              <option value="protect">Protect (Encrypt)</option>
              <option value="unlock">Unlock (Decrypt)</option>
            </select>
          </div>
          <div class="field">
            <label for="lock_password">Password</label>
            <input type="password" id="lock_password" placeholder="Enter password" />
          </div>
        </div>`
    },
    'rotate-watermark': {
      title: 'Rotate & Watermark',
      desc: 'Rotate all pages or add a diagonal semi-transparent watermark.',
      accept: '.pdf,application/pdf',
      multiple: false,
      minFiles: 1,
      action: null, // dynamic
      options: () => `
        <div class="field inline">
          <div class="field">
            <label for="rw_mode">Mode</label>
            <select id="rw_mode">
              <option value="rotate">Rotate</option>
              <option value="watermark">Watermark</option>
            </select>
          </div>
          <div class="field" id="rw_rotate_wrap">
            <label for="angle">Angle</label>
            <select id="angle">
              <option value="90">90°</option>
              <option value="180">180°</option>
              <option value="270">270°</option>
            </select>
          </div>
          <div class="field hidden" id="rw_text_wrap">
            <label for="wm_text">Watermark text</label>
            <input type="text" id="wm_text" placeholder="e.g. CONFIDENTIAL" />
          </div>
        </div>`
    }
  };

  function setBanner(type, msg) {
    if (!msg) {
      banner.className = 'banner hidden';
      banner.textContent = '';
      return;
    }
    banner.className = `banner ${type}`;
    banner.textContent = msg;
  }

  function setLoading(on, text) {
    if (on) {
      loading.classList.remove('hidden');
      loadingText.textContent = text || 'Processing locally…';
    } else {
      loading.classList.add('hidden');
    }
  }

  function formatBytes(bytes) {
    if (bytes == null || isNaN(bytes)) return '?';
    const units = ['B', 'KB', 'MB', 'GB'];
    let b = Number(bytes);
    let i = 0;
    while (b >= 1024 && i < units.length - 1) { b /= 1024; i++; }
    const digits = b >= 100 || i === 0 ? 0 : b >= 10 ? 1 : 2;
    return `${b.toFixed(digits)} ${units[i]}`;
  }
