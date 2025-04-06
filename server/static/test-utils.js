import fs from "fs";
import path from "path";

/**
 * Loads the HTML content from index.html
 * @returns {string} The HTML content
 */
export function loadIndexHtml() {
  const indexPath = path.resolve(__dirname, "index.html");
  return fs.readFileSync(indexPath, "utf8");
}

/**
 * Sets up the document with the HTML from index.html
 * @param {Document} document - The document to set up
 */
export function setupDocumentWithIndexHtml(document) {
  const html = loadIndexHtml();
  document.body.innerHTML = html;
}
