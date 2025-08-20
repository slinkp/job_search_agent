import { describe, expect, it, vi } from 'vitest';
import { formatDate, formatMessageDate, formatRecruiterMessageDate, isUrl, showError, showSuccess, confirmDialogs, errorLogger } from '../../static/ui-utils.js';

// Mock alert, confirm, and console for testing
global.alert = vi.fn();
global.confirm = vi.fn();
global.console = {
  ...console,
  error: vi.fn(),
  log: vi.fn()
};

describe('UI Utils', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('formatRecruiterMessageDate', () => {
    it('should return empty string for null/undefined input', () => {
      expect(formatRecruiterMessageDate(null)).toBe('');
      expect(formatRecruiterMessageDate(undefined)).toBe('');
      expect(formatRecruiterMessageDate('')).toBe('');
    });

    it('should format date correctly', () => {
      const testDate = new Date('2024-01-15T10:30:00');
      const result = formatRecruiterMessageDate(testDate.toISOString());
      
      // Should contain the expected format
      expect(result).toMatch(/2024\/01\/15/);
      expect(result).toMatch(/10:30am/);
      expect(result).toMatch(/\(.*days ago\)/);
    });
  });

  describe('formatMessageDate', () => {
    it('should return "Unknown date" for null/undefined input', () => {
      expect(formatMessageDate(null)).toBe('Unknown date');
      expect(formatMessageDate(undefined)).toBe('Unknown date');
      expect(formatMessageDate('')).toBe('Unknown date');
    });

    it('should format date correctly', () => {
      const testDate = new Date('2024-01-15T10:30:00');
      const result = formatMessageDate(testDate.toISOString());
      
      // Should contain locale date and time
      expect(result).toMatch(/1\/15\/2024/); // Locale date format
      expect(result).toMatch(/10:30/); // Time format
    });

    it('should handle invalid dates', () => {
      expect(formatMessageDate('invalid-date')).toBe('Invalid date');
    });
  });

  describe('showError', () => {
    it('should call alert with error message', () => {
      showError('Test error message');
      expect(alert).toHaveBeenCalledWith('Test error message');
    });
  });

  describe('showSuccess', () => {
    it('should call alert with success message', () => {
      showSuccess('Test success message');
      expect(alert).toHaveBeenCalledWith('Test success message');
    });
  });

  describe('isUrl', () => {
    it('should return true for valid URLs', () => {
      expect(isUrl('http://example.com')).toBe(true);
      expect(isUrl('https://example.com')).toBe(true);
      expect(isUrl('http://localhost:3000')).toBe(true);
    });

    it('should return false for invalid URLs', () => {
      expect(isUrl('not-a-url')).toBe(false);
      expect(isUrl('ftp://example.com')).toBe(false);
      expect(isUrl('')).toBe(false);
      expect(isUrl(null)).toBe(false);
      expect(isUrl(undefined)).toBe(false);
      expect(isUrl(123)).toBe(false);
    });
  });

  describe("formatDate", () => {
    it("formats date in simple format by default", () => {
      const result = formatDate("2023-12-01T10:30:00Z");
      expect(result).toMatch(/12\/1\/2023/); // Locale format may vary
      expect(result).toMatch(/\d{1,2}:\d{2}/); // Time should be included (any time format)
    });

    it("formats date in detailed format when specified", () => {
      const result = formatDate("2023-12-01T10:30:00Z", "detailed");
      expect(result).toMatch(/2023\/12\/01/);
      expect(result).toMatch(/\d{1,2}:\d{2}/); // Time should be included (any time format)
      expect(result).toMatch(/days ago/);
    });

    it("handles null/undefined dates in simple format", () => {
      expect(formatDate(null)).toBe("Unknown date");
      expect(formatDate(undefined)).toBe("Unknown date");
      expect(formatDate("")).toBe("Unknown date");
    });

    it("handles null/undefined dates in detailed format", () => {
      expect(formatDate(null, "detailed")).toBe("");
      expect(formatDate(undefined, "detailed")).toBe("");
      expect(formatDate("", "detailed")).toBe("");
    });

    it("handles invalid dates in simple format", () => {
      expect(formatDate("invalid-date")).toBe("Invalid date");
    });

    it("handles invalid dates in detailed format", () => {
      expect(formatDate("invalid-date", "detailed")).toBe("");
    });
  });

  describe('confirmDialogs', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should call confirm with archive without reply message', () => {
      confirmDialogs.archiveWithoutReply();
      expect(confirm).toHaveBeenCalledWith('Are you sure you want to archive this message without replying?');
    });

    it('should call confirm with send and archive message', () => {
      confirmDialogs.sendAndArchive();
      expect(confirm).toHaveBeenCalledWith('Are you sure you want to send this reply and archive the message?');
    });
  });

  describe('errorLogger', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should log failed to error with consistent formatting', () => {
      const error = new Error('Test error');
      errorLogger.logFailedTo('load messages', error);
      expect(console.error).toHaveBeenCalledWith('Failed to load messages:', error);
    });

    it('should log generic error with consistent formatting', () => {
      const error = new Error('Test error');
      errorLogger.logError('Custom error message', error);
      expect(console.error).toHaveBeenCalledWith('Custom error message', error);
    });
  });
}); 