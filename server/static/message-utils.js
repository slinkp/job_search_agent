/**
 * Message utility functions for the daily dashboard
 */

/**
 * Compute message preview text based on expansion state
 * @param {Object} message - The message object with a 'message' property
 * @param {boolean} isExpanded - Whether the message is expanded
 * @param {number} limit - Character limit for truncated preview (default: 200)
 * @returns {string} The preview text
 */
export function computeMessagePreview(message, isExpanded, limit = 200) {
  if (!message.message) return "No message content";

  let content = message.message;
  
  // Convert received_at to local time if exists
  if (message.received_at) {
    try {
      const utcDate = new Date(message.received_at);
      const localDate = new Date(utcDate.getTime() + utcDate.getTimezoneOffset() * 60000);
      const dateStr = localDate.toLocaleString();
      content = `[${dateStr}] ${content}`;
    } catch (e) {
      // Ignore date conversion errors
    }
  }

  if (isExpanded) {
    return content;
  }

  return content.length > limit
    ? content.substring(0, limit) + "..."
    : content;
}
