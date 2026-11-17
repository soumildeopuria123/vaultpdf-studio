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

  function renderTool() {
    const cfg = TOOLS[state.tool];
    toolHeading.textContent = cfg.title;
    toolDescription.textContent = cfg.desc;
    dropTitle.textContent = cfg.multiple ? 'Drag & drop files here' : 'Drag & drop a file here';
    dropSubtitle.textContent = 'or click to browse';
    fileInput.accept = cfg.accept || '';
    fileInput.multiple = !!cfg.multiple;
    optionsEl.innerHTML = cfg.options();
    reorderHint.classList.toggle('hidden', !cfg.reorder);
    redactArea.classList.toggle('hidden', state.tool !== 'redact');
    renderActions();
    renderFileList();
    bindOptionDynamics();
  }

  function bindOptionDynamics() {
    const imgMode = $('#img_mode');
    if (imgMode) {
      const sync = () => {
        const mode = imgMode.value;
        $('#img_fmt_wrap').classList.toggle('hidden', mode !== 'pdf-to-images');
        $('#img_dpi_wrap').classList.toggle('hidden', mode !== 'pdf-to-images');
        // adjust file input for mode
        if (mode === 'pdf-to-images') {
          fileInput.multiple = false;
          fileInput.accept = '.pdf,application/pdf';
          if (state.files.length > 1) state.files = state.files.slice(0, 1);
        } else {
          fileInput.multiple = true;
          fileInput.accept = '.png,.jpg,.jpeg,image/png,image/jpeg';
          state.files = state.files.filter(f => /\.(png|jpe?g)$/i.test(f.name));
        }
        renderFileList();
      };
      imgMode.addEventListener('change', sync);
      sync();
    }
    const convMode = $('#convert_mode');
    if (convMode) {
      const sync = () => {
        const mode = convMode.value;
        fileInput.multiple = false;
        fileInput.accept = mode === 'pdf-to-word' ? '.pdf,application/pdf' : '.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document';
        if (state.files.length > 1) state.files = state.files.slice(0, 1);
        renderFileList();
      };
      convMode.addEventListener('change', sync);
      sync();
    }
    const rwMode = $('#rw_mode');
    if (rwMode) {
      const sync = () => {
        const m = rwMode.value;
        $('#rw_rotate_wrap').classList.toggle('hidden', m !== 'rotate');
        $('#rw_text_wrap').classList.toggle('hidden', m !== 'watermark');
      };
      rwMode.addEventListener('change', sync);
      sync();
    }
  }

  function renderActions() {
    const cfg = TOOLS[state.tool];
    let label = cfg.action ? cfg.action.label : 'Run & Download';
    if (state.tool === 'convert-pdf-word') label = 'Convert & Download';
    if (state.tool === 'convert-pdf-images') label = 'Convert & Download';
    if (state.tool === 'protect-unlock') label = 'Process & Download';
    if (state.tool === 'rotate-watermark') label = 'Apply & Download';
    actionsEl.innerHTML = `<button class="btn primary" id="run-btn" type="button">${label}</button>`;
    $('#run-btn').addEventListener('click', onRun);
  }

  function renderFileList() {
    fileListEl.innerHTML = '';
    const cfg = TOOLS[state.tool];
    state.files.forEach((f, idx) => {
      const li = document.createElement('li');
      li.className = 'file-item';
      const left = document.createElement('div');
      left.innerHTML = `<div class="name">${escapeHtml(f.name)}</div><div class="meta">${formatBytes(f.size)}</div>`;
      const actions = document.createElement('div');
      actions.className = 'file-actions';
      if (cfg.reorder && state.files.length > 1) {
        const up = document.createElement('button');
        up.type = 'button'; up.className = 'icon-btn'; up.textContent = '↑';
        up.title = 'Move up';
        up.disabled = idx === 0;
        up.addEventListener('click', () => { moveFile(idx, -1); });
        const down = document.createElement('button');
        down.type = 'button'; down.className = 'icon-btn'; down.textContent = '↓';
        down.title = 'Move down';
        down.disabled = idx === state.files.length - 1;
        down.addEventListener('click', () => { moveFile(idx, 1); });
        actions.appendChild(up); actions.appendChild(down);
      }
      const rm = document.createElement('button');
      rm.type = 'button'; rm.className = 'icon-btn'; rm.textContent = '✕';
      rm.title = 'Remove';
      rm.addEventListener('click', () => { removeFile(idx); });
      actions.appendChild(rm);
      li.appendChild(left); li.appendChild(actions);
      fileListEl.appendChild(li);
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
  }

  function moveFile(idx, delta) {
    const j = idx + delta;
    if (j < 0 || j >= state.files.length) return;
    const arr = state.files.slice();
    const [item] = arr.splice(idx, 1);
    arr.splice(j, 0, item);
    state.files = arr;
    renderFileList();
  }

  function removeFile(idx) {
    state.files.splice(idx, 1);
    renderFileList();
    if (state.tool === 'redact') {
      initRedactIfNeeded();
    }
  }

  function setFiles(fileList) {
    const cfg = TOOLS[state.tool];
    let files = Array.from(fileList || []);
    if (!cfg.multiple) files = files.slice(0, 1);
    if (cfg.multiple && (state.tool === 'merge' || state.tool === 'convert-pdf-images')) {
      // append for reorderable multi-file tools if adding
      // but here setFiles replaces; caller decides
    }
    state.files = files;
    renderFileList();
    if (state.tool === 'redact') initRedactIfNeeded();
  }

  function addFiles(fileList) {
    const cfg = TOOLS[state.tool];
    let files = Array.from(fileList || []);
    if (!cfg.multiple) {
      state.files = files.slice(0, 1);
    } else {
      state.files = state.files.concat(files);
    }
    renderFileList();
    if (state.tool === 'redact') initRedactIfNeeded();
  }

  async function initRedactIfNeeded() {
    if (state.tool !== 'redact') return;
    if (!state.redact) {
      state.redact = new window.RedactorCanvas(redactCanvasEl, redactPageInfo);
    }
    if (state.files.length === 1) {
      try {
        setLoading(true, 'Rendering PDF preview…');
        await state.redact.setPdfFile(state.files[0]);
        setBanner('', '');
      } catch (e) {
        setBanner('error', e.message || 'Failed to load PDF for redaction.');
        state.redact.reset();
      } finally {
        setLoading(false);
      }
    } else {
      state.redact.reset();
    }
  }

  async function onRun() {
    setBanner('', '');
    const cfg = TOOLS[state.tool];
    try {
      if (!state.files.length) throw new Error('Please select a file first.');
      if (cfg.minFiles && state.files.length < cfg.minFiles) {
        throw new Error(`Please select at least ${cfg.minFiles} file(s).`);
      }
      let endpoint = cfg.action ? cfg.action.endpoint : null;
      const fd = new FormData();

      if (state.tool === 'merge') {
        state.files.forEach(f => fd.append('files', f));
      } else if (state.tool === 'split') {
        const ranges = $('#ranges').value.trim();
        if (!ranges) throw new Error('Please enter page ranges (e.g. 1-3, 5).');
        fd.append('file', state.files[0]);
        fd.append('ranges', ranges);
      } else if (state.tool === 'compress') {
        const kb = parseFloat($('#target_kb').value);
        if (!kb || kb <= 0) throw new Error('Please enter a valid target size in KB.');
        fd.append('file', state.files[0]);
        fd.append('target_kb', String(kb));
      } else if (state.tool === 'redact') {
        if (!state.redact || !state.redact.pdfFile) throw new Error('Please load a PDF first.');
        const boxes = state.redact.getBoxes();
        if (!boxes.length) throw new Error('Please draw at least one redaction box before applying.');
        fd.append('file', state.files[0]);
        fd.append('boxes', JSON.stringify(boxes));
      } else if (state.tool === 'convert-pdf-word') {
        const mode = $('#convert_mode').value;
        const f = state.files[0];
        if (mode === 'pdf-to-word') {
          if (!/\.pdf$/i.test(f.name)) throw new Error('Please select a PDF file for PDF → Word.');
          endpoint = '/api/convert/pdf-to-word';
        } else {
          if (!/\.docx$/i.test(f.name)) throw new Error('Please select a .docx file for Word → PDF.');
          endpoint = '/api/convert/word-to-pdf';
        }
        fd.append('file', f);
      } else if (state.tool === 'convert-pdf-images') {
        const mode = $('#img_mode').value;
        if (mode === 'pdf-to-images') {
          if (!/\.pdf$/i.test(state.files[0].name)) throw new Error('Please select a PDF file.');
          endpoint = '/api/convert/pdf-to-images';
          fd.append('file', state.files[0]);
          fd.append('fmt', $('#img_fmt').value);
          fd.append('dpi', $('#img_dpi').value || '150');
        } else {
          if (state.files.some(f => !/\.(png|jpe?g)$/i.test(f.name))) throw new Error('Please select only PNG/JPG images.');
          endpoint = '/api/convert/images-to-pdf';
          state.files.forEach(f => fd.append('files', f));
        }
      } else if (state.tool === 'protect-unlock') {
        const mode = $('#lock_mode').value;
        const pw = $('#lock_password').value;
        if (mode === 'protect' && !pw) throw new Error('Please enter a password to protect the PDF.');
        endpoint = mode === 'protect' ? '/api/protect' : '/api/unlock';
        fd.append('file', state.files[0]);
        fd.append('password', pw);
      } else if (state.tool === 'rotate-watermark') {
        const mode = $('#rw_mode').value;
        if (mode === 'rotate') {
          endpoint = '/api/rotate';
          fd.append('file', state.files[0]);
          fd.append('angle', $('#angle').value);
        } else {
          const text = $('#wm_text').value.trim();
          if (!text) throw new Error('Please enter watermark text.');
          endpoint = '/api/watermark';
          fd.append('file', state.files[0]);
          fd.append('text', text);
        }
      }

      if (!endpoint) throw new Error('Unknown action.');
      setLoading(true, 'Processing locally…');
      const res = await fetch(endpoint, { method: 'POST', body: fd });
      if (!res.ok) {
        let msg = 'Request failed.';
        try { const j = await res.json(); msg = j.error || j.detail || msg; } catch (_) {}
        throw new Error(msg);
      }
      const blob = await res.blob();
      const filename = getFilenameFromResponse(res) || 'output';
      triggerDownload(blob, filename);

      if (state.tool === 'compress') {
        const orig = res.headers.get('X-Original-Size');
        const fin = res.headers.get('X-Final-Size');
        const met = res.headers.get('X-Target-Met') === 'true';
        const msg = `${formatBytes(orig)} → ${formatBytes(fin)}` + (met ? ' (target met)' : ' (best effort; target not fully met)');
        setBanner('success', `Compression complete: ${msg}`);
      } else {
        setBanner('success', `Done. Downloaded ${filename}. Temporary files auto-wiped.`);
      }
    } catch (e) {
      setBanner('error', e.message || 'An error occurred.');
    } finally {
      setLoading(false);
    }
  }

  function getFilenameFromResponse(res) {
    const cd = res.headers.get('Content-Disposition') || '';
    const m = /filename\*?=(?:UTF-8''|"?)([^";\n]+)/i.exec(cd);
    if (m && m[1]) {
      try { return decodeURIComponent(m[1].replace(/"/g, '').trim()); } catch (_) { return m[1].replace(/"/g, '').trim(); }
    }
    return null;
  }

  function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  // Tool selection
  toolGrid.addEventListener('click', (e) => {
    const btn = e.target.closest('.tool-card');
    if (!btn) return;
    const tool = btn.dataset.tool;
    if (!tool || !TOOLS[tool]) return;
    state.tool = tool;
    state.files = [];
    document.querySelectorAll('.tool-card').forEach(el => el.classList.toggle('active', el === btn));
    setBanner('', '');
    renderTool();
    if (state.redact) state.redact.reset();
  });

  // Drop zone
  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    const cfg = TOOLS[state.tool];
    if (cfg.multiple && (state.tool === 'merge' || ($('#img_mode') && $('#img_mode').value === 'images-to-pdf'))) {
      addFiles(e.target.files);
    } else {
      setFiles(e.target.files);
    }
    fileInput.value = '';
  });
  ['dragenter', 'dragover'].forEach(ev => dropZone.addEventListener(ev, (e) => {
    e.preventDefault(); e.stopPropagation(); dropZone.classList.add('dragover');
  }));
  ['dragleave', 'drop'].forEach(ev => dropZone.addEventListener(ev, (e) => {
    e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('dragover');
  }));
  dropZone.addEventListener('drop', (e) => {
    const cfg = TOOLS[state.tool];
    const files = e.dataTransfer.files;
    if (cfg.multiple && (state.tool === 'merge' || ($('#img_mode') && $('#img_mode').value === 'images-to-pdf'))) {
      addFiles(files);
    } else {
      setFiles(files);
    }
  });

  // Redact toolbar
  $('#redact-prev').addEventListener('click', async () => {
    if (!state.redact) return;
    try { setLoading(true, 'Loading page…'); await state.redact.prevPage(); }
    catch (e) { setBanner('error', e.message); }
    finally { setLoading(false); }
  });
  $('#redact-next').addEventListener('click', async () => {
    if (!state.redact) return;
    try { setLoading(true, 'Loading page…'); await state.redact.nextPage(); }
    catch (e) { setBanner('error', e.message); }
    finally { setLoading(false); }
  });
  $('#redact-clear-page').addEventListener('click', () => { if (state.redact) state.redact.clearPageBoxes(); });
  $('#redact-clear-all').addEventListener('click', () => { if (state.redact) state.redact.clearAllBoxes(); });

  // Initial render
  renderTool();
})();
