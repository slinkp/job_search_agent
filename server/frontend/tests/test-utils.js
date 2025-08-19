import fs from "fs";
import path from "path";

/**
 * Loads the HTML content from index.html
 * @returns {string} The HTML content
 */
export function loadIndexHtml() {
  const indexPath = path.resolve(__dirname, "../../static/index.html");
  return fs.readFileSync(indexPath, "utf8");
}

/**
 * Remove external script tags so the test DOM does not try to fetch them.
 * Keeps the rest of the HTML intact for structural assertions.
 *
 * This avoids happy-dom attempting to load module scripts like /static/app.js.
 */
export function stripExternalScripts(html) {
  let sanitized = html;
  // Remove any <script ... src="..."></script> tags (module or otherwise)
  sanitized = sanitized.replace(/<script\b[^>]*src=["'][^"']+["'][^>]*>\s*<\/script>/gi, "");
  // Remove stylesheet links to avoid happy-dom fetching CSS
  sanitized = sanitized.replace(/<link\b[^>]*rel=["']stylesheet["'][^>]*>/gi, "");
  return sanitized;
}

/**
 * Sets up the document with the HTML from index.html
 * @param {Document} document - The document to set up
 */
export function setupDocumentWithIndexHtml(document) {
  const rawHtml = loadIndexHtml();
  const sanitizedHtml = stripExternalScripts(rawHtml);
  document.body.innerHTML = sanitizedHtml;
}
