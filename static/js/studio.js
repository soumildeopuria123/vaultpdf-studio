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
