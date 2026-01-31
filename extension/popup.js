const BACKEND_URL = 'http://localhost:8000';

const statusEl = document.getElementById('status');
const progressEl = document.getElementById('progress');
const syncBtn = document.getElementById('syncBtn');
const debugBtn = document.getElementById('debugBtn');
const batchLimitInput = document.getElementById('batchLimit');
const resultsEl = document.getElementById('results');
const errorMessageEl = document.getElementById('errorMessage');
const debugResultsEl = document.getElementById('debugResults');

// Store last debug snapshot for copy functionality
let lastDebugSnapshot = null;

// Load saved batch limit
chrome.storage.local.get(['batchLimit'], (result) => {
  if (result.batchLimit) {
    batchLimitInput.value = result.batchLimit;
  }
});

// Save batch limit on change
batchLimitInput.addEventListener('change', () => {
  chrome.storage.local.set({ batchLimit: parseInt(batchLimitInput.value) });
});

function setStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
}

function showProgress(show) {
  progressEl.className = show ? 'progress-container visible' : 'progress-container';
}

function showResults(data) {
  document.getElementById('newCount').textContent = data.new_count;
  document.getElementById('dupCount').textContent = data.duplicate_count;
  document.getElementById('failCount').textContent = data.failed_count;
  resultsEl.className = 'results visible';
}

function showError(message) {
  errorMessageEl.textContent = message;
  errorMessageEl.className = 'error-message visible';
}

function hideError() {
  errorMessageEl.className = 'error-message';
}

async function checkBackendHealth() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    return response.ok;
  } catch (e) {
    return false;
  }
}

syncBtn.addEventListener('click', async () => {
  hideError();
  resultsEl.className = 'results';

  // Check if backend is running
  const backendHealthy = await checkBackendHealth();
  if (!backendHealthy) {
    showError('Backend is not running. Start the server with: uvicorn app.main:app --reload');
    setStatus('Backend unavailable', 'error');
    return;
  }

  // Get the current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Check if on bookmarks page
  const isBookmarksPage = tab.url.includes('twitter.com/i/bookmarks') ||
                          tab.url.includes('x.com/i/bookmarks');

  if (!isBookmarksPage) {
    showError('Navigate to Twitter bookmarks first (twitter.com/i/bookmarks)');
    setStatus('Wrong page', 'error');
    return;
  }

  // Start sync
  setStatus('Processing...', 'processing');
  showProgress(true);
  syncBtn.disabled = true;

  const batchLimit = parseInt(batchLimitInput.value) || 50;
  const skipDuplicates = document.getElementById('skipDuplicates').checked;

  try {
    // Send message to content script to scrape bookmarks
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'scrapeBookmarks',
      batchLimit: batchLimit,
      skipDuplicates: skipDuplicates
    });

    showProgress(false);

    if (response.error) {
      showError(response.error);
      setStatus('Failed', 'error');
    } else if (response.success) {
      showResults(response.data);
      setStatus('Sync complete!', 'success');
    }
  } catch (e) {
    showProgress(false);
    showError(`Error: ${e.message}`);
    setStatus('Failed', 'error');
  }

  syncBtn.disabled = false;
});

// Debug button handler
debugBtn.addEventListener('click', async () => {
  hideError();
  debugResultsEl.className = 'debug-results';

  // Get the current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Check if on bookmarks page
  const isBookmarksPage = tab.url.includes('twitter.com/i/bookmarks') ||
                          tab.url.includes('x.com/i/bookmarks');

  if (!isBookmarksPage) {
    showError('Navigate to Twitter bookmarks first (twitter.com/i/bookmarks)');
    setStatus('Wrong page', 'error');
    return;
  }

  setStatus('Generating debug snapshot...', 'processing');
  debugBtn.disabled = true;

  try {
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'generateDebugSnapshot'
    });

    if (response.error) {
      showError(response.error);
      setStatus('Debug failed', 'error');
    } else {
      lastDebugSnapshot = response.snapshot;
      showDebugResults(response.snapshot);
      setStatus('Debug snapshot ready', 'success');
    }
  } catch (e) {
    showError(`Error: ${e.message}`);
    setStatus('Debug failed', 'error');
  }

  debugBtn.disabled = false;
});

function showDebugResults(snapshot) {
  document.getElementById('debugTotal').textContent = snapshot.totalArticlesFound;
  document.getElementById('debugCaptured').textContent = snapshot.summary.captured;
  document.getElementById('debugSkipped').textContent = snapshot.summary.skipped;

  // Show skip reasons
  const skipReasonsList = document.getElementById('skipReasonsList');
  skipReasonsList.innerHTML = '';

  const reasons = snapshot.summary.skipReasons;
  if (Object.keys(reasons).length === 0) {
    skipReasonsList.innerHTML = '<div>None - all items captured!</div>';
  } else {
    for (const [reason, count] of Object.entries(reasons)) {
      const div = document.createElement('div');
      div.style.display = 'flex';
      div.style.justifyContent = 'space-between';
      div.innerHTML = `<span>${reason}:</span><span>${count}</span>`;
      skipReasonsList.appendChild(div);
    }
  }

  debugResultsEl.className = 'debug-results visible';
}

// Copy debug report button
document.getElementById('copyDebugBtn').addEventListener('click', () => {
  if (!lastDebugSnapshot) return;

  const report = JSON.stringify(lastDebugSnapshot, null, 2);
  navigator.clipboard.writeText(report).then(() => {
    const btn = document.getElementById('copyDebugBtn');
    btn.textContent = 'Copied!';
    setTimeout(() => {
      btn.textContent = 'Copy Full Report';
    }, 2000);
  });
});
