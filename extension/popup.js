const BACKEND_URL = 'http://localhost:8000';

const statusEl = document.getElementById('status');
const progressEl = document.getElementById('progress');
const syncBtn = document.getElementById('syncBtn');
const batchLimitInput = document.getElementById('batchLimit');
const resultsEl = document.getElementById('results');
const errorMessageEl = document.getElementById('errorMessage');

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
