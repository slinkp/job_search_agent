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

  if (isExpanded) {
    return message.message;
  }

  return message.message.length > limit
    ? message.message.substring(0, limit) + "..."
    : message.message;
}
