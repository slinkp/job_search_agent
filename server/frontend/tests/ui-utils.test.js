import { describe, expect, it, vi } from 'vitest';
import { formatMessageDate, formatRecruiterMessageDate, isUrl, showError, showSuccess } from '../../static/ui-utils.js';

// Mock alert for testing
global.alert = vi.fn();

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
      expect(formatMessageDate('invalid-date')).toBe('Invalid Date Invalid Date');
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
}); 