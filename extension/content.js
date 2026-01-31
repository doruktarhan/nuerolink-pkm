const BACKEND_URL = 'http://localhost:8000';

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'scrapeBookmarks') {
    scrapeAndSync(message.batchLimit, message.skipDuplicates)
      .then(sendResponse)
      .catch(err => sendResponse({ error: err.message }));
    return true; // Keep channel open for async response
  }

  if (message.action === 'generateDebugSnapshot') {
    generateDebugSnapshot()
      .then(sendResponse)
      .catch(err => sendResponse({ error: err.message }));
    return true;
  }
});

async function scrapeAndSync(batchLimit, skipDuplicates = false) {
  const collectedItems = new Map();
  let lastHeight = 0;
  let noNewContentCount = 0;
  let duplicatesFound = false;

  // Expand all "Show more" buttons before initial scrape
  await expandAllShowMore();

  // Initial scrape
  scrapeVisibleTweets(collectedItems);

  // Auto-scroll to find more bookmarks
  while (collectedItems.size < batchLimit && noNewContentCount < 3 && !duplicatesFound) {
    // Scroll down
    window.scrollTo(0, document.body.scrollHeight);

    // Wait for content to load
    await sleep(1500);

    // Expand any new "Show more" buttons that appeared
    await expandAllShowMore();

    const previousSize = collectedItems.size;
    scrapeVisibleTweets(collectedItems);

    // Check if we found new content
    if (collectedItems.size === previousSize) {
      noNewContentCount++;
    } else {
      noNewContentCount = 0;
    }

    // Check if we've reached the limit
    if (collectedItems.size >= batchLimit) {
      break;
    }

    // Check for page height change (indicates end of content)
    const currentHeight = document.body.scrollHeight;
    if (currentHeight === lastHeight) {
      noNewContentCount++;
    }
    lastHeight = currentHeight;
  }

  // Convert to array and limit
  let items = Array.from(collectedItems.values()).slice(0, batchLimit);

  if (items.length === 0) {
    return { error: 'No bookmarks found on this page' };
  }

  // Send to backend
  try {
    const response = await fetch(`${BACKEND_URL}/api/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        items: items,
        platform: 'twitter',
        skip_duplicates: skipDuplicates
      })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();

    return { success: true, data: data };
  } catch (err) {
    return { error: `Failed to sync: ${err.message}` };
  }
}

/**
 * Click all "Show more" buttons to expand truncated tweet text.
 */
async function expandAllShowMore() {
  const showMoreButtons = document.querySelectorAll('[data-testid="tweet-text-show-more-link"]');

  for (const button of showMoreButtons) {
    try {
      button.click();
      await sleep(300); // Wait for expansion
    } catch (e) {
      console.log('[NeuroLink] Failed to click Show more:', e);
    }
  }
}

/**
 * Scrape all visible tweets/articles from the page.
 * Detects content type and extracts appropriate content.
 */
function scrapeVisibleTweets(collectedItems) {
  // Find all article elements (tweets and articles)
  const articles = document.querySelectorAll('article[data-testid="tweet"]');

  console.log(`[NeuroLink] Found ${articles.length} articles on page`);

  articles.forEach((article, index) => {
    // Find the tweet link to get URL
    const tweetLink = article.querySelector('a[href*="/status/"]');
    if (!tweetLink) {
      console.log(`[NeuroLink] Article ${index}: No status link found`);
      return;
    }

    const href = tweetLink.getAttribute('href');
    const match = href.match(/\/([^\/]+)\/status\/(\d+)/);
    if (!match) {
      console.log(`[NeuroLink] Article ${index}: URL pattern didn't match: ${href}`);
      return;
    }

    const username = match[1];
    const tweetId = match[2];

    // Skip if it's a retweet indicator or other non-tweet link
    if (username === 'i' || href.includes('/analytics') || href.includes('/retweets')) {
      console.log(`[NeuroLink] Article ${index}: Skipped (retweet/analytics): ${href}`);
      return;
    }

    const fullUrl = `https://twitter.com/${username}/status/${tweetId}`;

    // Skip if already collected
    if (collectedItems.has(fullUrl)) {
      console.log(`[NeuroLink] Article ${index}: Already collected: ${fullUrl}`);
      return;
    }

    // Detect content type and extract content
    const contentData = extractContentFromArticle(article);

    console.log(`[NeuroLink] Article ${index}: Collected ${contentData.extra_data.content_type} - ${fullUrl}`);
    console.log(`[NeuroLink]   Content: ${contentData.fullContent ? contentData.fullContent.slice(0, 50) + '...' : 'NULL'}`);

    collectedItems.set(fullUrl, {
      url: fullUrl,
      preview_text: contentData.previewText,
      full_content: contentData.fullContent,
      thread_content: null, // Thread extraction is Phase 2
      extra_data: contentData.extra_data
    });
  });
}

/**
 * Extract content and extra_data from a tweet/article element.
 * Handles both regular tweets and Twitter Articles.
 */
function extractContentFromArticle(article) {
  const extra_data = {
    content_type: 'tweet',
    has_images: false,
    image_count: 0,
    image_urls: [],
    has_video: false,
    has_quote: false,
    quoted_author: null,
    quoted_text: null,
    has_show_more: false,
    article_title: null,
    article_description: null,
    article_cover_url: null
  };

  let previewText = null;
  let fullContent = null;

  // Check if this is an Article
  const articleCover = article.querySelector('[data-testid="article-cover-image"]');

  if (articleCover) {
    // This is a Twitter Article
    extra_data.content_type = 'article';

    // Get cover image
    const coverImg = articleCover.querySelector('img');
    if (coverImg) {
      extra_data.article_cover_url = coverImg.src;
    }

    // Extract article title and description
    // They appear in specific divs after the cover image
    const contentArea = article.querySelector('[class*="r-xyw6el"]');
    if (contentArea) {
      const textDivs = contentArea.querySelectorAll('div[dir="auto"]');
      if (textDivs.length >= 1) {
        extra_data.article_title = textDivs[0].innerText;
        fullContent = textDivs[0].innerText;
        previewText = textDivs[0].innerText;
      }
      if (textDivs.length >= 2) {
        extra_data.article_description = textDivs[1].innerText;
        fullContent = `${extra_data.article_title}\n\n${extra_data.article_description}`;
      }
    }

    // Fallback: try to find any prominent text
    if (!fullContent) {
      const allSpans = article.querySelectorAll('span[class*="r-bcqeeo"]');
      for (const span of allSpans) {
        const text = span.innerText;
        if (text && text.length > 20 && !text.startsWith('@')) {
          fullContent = text;
          previewText = text.slice(0, 500);
          break;
        }
      }
    }

  } else {
    // This is a regular tweet
    extra_data.content_type = 'tweet';

    // Check for "Show more" button (indicates truncated text)
    const showMoreBtn = article.querySelector('[data-testid="tweet-text-show-more-link"]');
    extra_data.has_show_more = !!showMoreBtn;

    // Get main tweet text (first tweetText that's not inside a quoted tweet)
    const allTweetTexts = article.querySelectorAll('[data-testid="tweetText"]');

    // The first tweetText is the main tweet (unless it's inside a quote)
    if (allTweetTexts.length > 0) {
      // Check if first tweetText is the main tweet or quoted tweet
      const firstTweetText = allTweetTexts[0];
      const isInQuote = firstTweetText.closest('[role="link"][tabindex="0"]');

      if (!isInQuote) {
        fullContent = firstTweetText.innerText;
        previewText = fullContent.slice(0, 500);
      } else if (allTweetTexts.length > 1) {
        // First one was quote, check second
        fullContent = allTweetTexts[1].innerText;
        previewText = fullContent.slice(0, 500);
      }
    }

    // Check for quoted tweet
    const quotedSection = article.querySelector('[role="link"][tabindex="0"]');
    if (quotedSection) {
      const quotedTweetText = quotedSection.querySelector('[data-testid="tweetText"]');
      const quotedUserName = quotedSection.querySelector('[data-testid="User-Name"]');

      if (quotedTweetText) {
        extra_data.has_quote = true;
        extra_data.quoted_text = quotedTweetText.innerText;

        if (quotedUserName) {
          const usernameLink = quotedUserName.querySelector('a[href^="/"]');
          if (usernameLink) {
            extra_data.quoted_author = usernameLink.getAttribute('href').replace('/', '');
          }
        }
      }
    }

    // Check for images
    const photos = article.querySelectorAll('[data-testid="tweetPhoto"]');
    if (photos.length > 0) {
      extra_data.has_images = true;
      extra_data.image_count = photos.length;
      photos.forEach(photo => {
        const img = photo.querySelector('img');
        if (img && img.src) {
          extra_data.image_urls.push(img.src);
        }
      });
    }

    // Check for video
    const video = article.querySelector('[data-testid="videoPlayer"]');
    if (video) {
      extra_data.has_video = true;
    }
  }

  return {
    previewText,
    fullContent,
    extra_data
  };
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Generate a structured debug snapshot for AI analysis.
 * Captures what the extension sees vs what it would capture.
 */
async function generateDebugSnapshot() {
  // Find all candidate article elements
  const articles = document.querySelectorAll('article[data-testid="tweet"]');

  const snapshot = {
    timestamp: Date.now(),
    url: window.location.href,
    totalArticlesFound: articles.length,
    items: [],
    summary: {
      captured: 0,
      skipped: 0,
      skipReasons: {}
    }
  };

  articles.forEach((article, index) => {
    const item = analyzeArticleForDebug(article, index);
    snapshot.items.push(item);

    if (item.wouldCapture) {
      snapshot.summary.captured++;
    } else {
      snapshot.summary.skipped++;
      const reason = item.skipReason || 'UNKNOWN';
      snapshot.summary.skipReasons[reason] = (snapshot.summary.skipReasons[reason] || 0) + 1;
    }
  });

  // Send to backend for storage
  try {
    const response = await fetch(`${BACKEND_URL}/api/debug`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(snapshot)
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    return { success: true, snapshot, savedAs: data.id };
  } catch (err) {
    // Return snapshot even if backend save fails
    return { success: false, snapshot, error: err.message };
  }
}

/**
 * Analyze a single article element for debugging.
 * Returns structured info about what the extension sees and why it would skip/capture.
 */
function analyzeArticleForDebug(article, index) {
  const result = {
    index,
    wouldCapture: false,
    skipReason: null,

    // Detection signals
    hasStatusLink: false,
    statusLinkHref: null,
    extractedUrl: null,
    extractedUsername: null,

    // Content type signals
    hasArticleCover: false,
    hasTweetText: false,
    hasVideo: false,
    hasImages: false,
    imageCount: 0,

    // All data-testid attributes found
    dataTestIds: [],

    // All href links found (for debugging URL patterns)
    allHrefs: [],

    // Text preview (first 200 chars)
    textPreview: null,

    // DOM fingerprint
    tagName: article.tagName,
    outerHTMLLength: article.outerHTML.length
  };

  // Collect all data-testid attributes
  const testIdElements = article.querySelectorAll('[data-testid]');
  testIdElements.forEach(el => {
    const testId = el.getAttribute('data-testid');
    if (!result.dataTestIds.includes(testId)) {
      result.dataTestIds.push(testId);
    }
  });

  // Collect all href links
  const links = article.querySelectorAll('a[href]');
  links.forEach(link => {
    const href = link.getAttribute('href');
    if (href && !result.allHrefs.includes(href)) {
      result.allHrefs.push(href);
    }
  });

  // Check for status link (the key selector)
  const tweetLink = article.querySelector('a[href*="/status/"]');
  result.hasStatusLink = !!tweetLink;

  if (!tweetLink) {
    result.skipReason = 'NO_STATUS_LINK';

    // Try to find what links ARE present for debugging
    const anyLinks = article.querySelectorAll('a[href*="/"]');
    if (anyLinks.length > 0) {
      result.alternativeLinks = Array.from(anyLinks).slice(0, 5).map(l => l.getAttribute('href'));
    }

    return result;
  }

  result.statusLinkHref = tweetLink.getAttribute('href');

  // Check regex match
  const href = result.statusLinkHref;
  const match = href.match(/\/([^\/]+)\/status\/(\d+)/);

  if (!match) {
    result.skipReason = 'REGEX_MISMATCH';
    return result;
  }

  result.extractedUsername = match[1];
  const tweetId = match[2];

  // Check for skip conditions
  if (result.extractedUsername === 'i') {
    result.skipReason = 'USERNAME_IS_I';
    return result;
  }

  if (href.includes('/analytics') || href.includes('/retweets')) {
    result.skipReason = 'ANALYTICS_OR_RETWEETS';
    return result;
  }

  result.extractedUrl = `https://twitter.com/${result.extractedUsername}/status/${tweetId}`;
  result.wouldCapture = true;

  // Content type detection
  result.hasArticleCover = !!article.querySelector('[data-testid="article-cover-image"]');
  result.hasTweetText = !!article.querySelector('[data-testid="tweetText"]');
  result.hasVideo = !!article.querySelector('[data-testid="videoPlayer"]');

  const photos = article.querySelectorAll('[data-testid="tweetPhoto"]');
  result.hasImages = photos.length > 0;
  result.imageCount = photos.length;

  // Text preview
  const tweetText = article.querySelector('[data-testid="tweetText"]');
  if (tweetText) {
    result.textPreview = tweetText.innerText.slice(0, 200);
  } else if (result.hasArticleCover) {
    // Try to get article title
    const contentArea = article.querySelector('[class*="r-xyw6el"]');
    if (contentArea) {
      const textDivs = contentArea.querySelectorAll('div[dir="auto"]');
      if (textDivs.length > 0) {
        result.textPreview = textDivs[0].innerText.slice(0, 200);
      }
    }
  }

  return result;
}
