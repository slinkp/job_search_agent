import { describe, expect, it, vi } from 'vitest';
import { setIncludeAllParam, buildHashForCompany, parseViewFromUrl, urlUtils } from '../../static/url-utils.js';

// Mock window.location and history
const mockLocation = {
  href: 'http://localhost:3000/test?param=value#hash',
  search: '?param=value',
  hash: '#hash',
  pathname: '/test',
  origin: 'http://localhost:3000',
  protocol: 'http:',
  host: 'localhost:3000',
  hostname: 'localhost',
  port: '3000'
};

const mockHistory = {
  replaceState: vi.fn(),
  pushState: vi.fn()
};

Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true
});

Object.defineProperty(window, 'history', {
  value: mockHistory,
  writable: true
});

// Mock URL constructor to work with our mock location
const originalURL = global.URL;
global.URL = class MockURL {
  constructor(input, base) {
    if (input === window.location) {
      return new originalURL('http://localhost:3000/test?param=value#hash');
    }
    return new originalURL(input, base);
  }
};

describe('URL Utils', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('setIncludeAllParam', () => {
    it('should set include_all parameter when includeAll is true', () => {
      const url = new URL('http://localhost:3000/test');
      setIncludeAllParam(url, true);
      expect(url.searchParams.get('include_all')).toBe('true');
    });

    it('should remove include_all parameter when includeAll is false', () => {
      const url = new URL('http://localhost:3000/test?include_all=true');
      setIncludeAllParam(url, false);
      expect(url.searchParams.get('include_all')).toBeNull();
    });
  });

  describe('buildHashForCompany', () => {
    it('should build hash for company ID', () => {
      const result = buildHashForCompany('company-123');
      expect(result).toBe('#company-123');
    });

    it('should encode special characters in company ID', () => {
      const result = buildHashForCompany('company with spaces');
      expect(result).toBe('#company%20with%20spaces');
    });
  });

  describe('parseViewFromUrl', () => {
    it('should return daily_dashboard for view=daily', () => {
      const result = parseViewFromUrl('?view=daily');
      expect(result).toBe('daily_dashboard');
    });

    it('should return company_management for other values', () => {
      const result = parseViewFromUrl('?view=other');
      expect(result).toBe('company_management');
    });

    it('should return company_management for no view parameter', () => {
      const result = parseViewFromUrl('?other=value');
      expect(result).toBe('company_management');
    });
  });

  describe('urlUtils', () => {
    describe('createUrl', () => {
      it('should create URL from current location', () => {
        const url = urlUtils.createUrl();
        expect(url.href).toBe('http://localhost:3000/test?param=value#hash');
      });
    });

    describe('updateUrlParams', () => {
      it('should update URL parameters and replace state by default', () => {
        const url = urlUtils.updateUrlParams({ newParam: 'value' });
        expect(mockHistory.replaceState).toHaveBeenCalledWith({}, '', url);
        expect(url.searchParams.get('newParam')).toBe('value');
      });

      it('should push state when replaceState is false', () => {
        const url = urlUtils.updateUrlParams({ newParam: 'value' }, false);
        expect(mockHistory.pushState).toHaveBeenCalledWith({}, '', url);
        expect(url.searchParams.get('newParam')).toBe('value');
      });

      it('should remove parameters when value is null', () => {
        const url = urlUtils.updateUrlParams({ param: null });
        expect(url.searchParams.get('param')).toBeNull();
      });
    });

    describe('removeUrlParams', () => {
      it('should remove specified URL parameters', () => {
        const url = urlUtils.removeUrlParams(['param']);
        expect(mockHistory.replaceState).toHaveBeenCalledWith({}, '', url);
        expect(url.searchParams.get('param')).toBeNull();
      });
    });

    describe('setHash', () => {
      it('should set URL hash', () => {
        const url = urlUtils.setHash('#new-hash');
        expect(mockHistory.replaceState).toHaveBeenCalledWith({}, '', url);
        expect(url.hash).toBe('#new-hash');
      });
    });
  });
});
