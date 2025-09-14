/**
 * Company Logo Mapping System
 * Maps company names to their corresponding SVG logos with unique IDs
 * Only includes companies with actual SVG assets
 */

export interface CompanyInfo {
  id: string;
  name: string;
  displayName: string;
  logoPath: string;
  primaryColor: string;
  secondaryColor?: string;
}

export const COMPANY_LOGOS: Record<string, CompanyInfo> = {
  // Tech Giants (only companies with actual SVG assets)
  microsoft: {
    id: 'microsoft',
    name: 'Microsoft',
    displayName: 'Microsoft',
    logoPath: '/attached_assets/logos/microsoft.svg',
    primaryColor: '#00BCF2',
    secondaryColor: '#0078D4',
  },
  google: {
    id: 'google',
    name: 'Google',
    displayName: 'Google',
    logoPath: '/attached_assets/logos/google.svg',
    primaryColor: '#4285F4',
    secondaryColor: '#DB4437',
  },
  apple: {
    id: 'apple',
    name: 'Apple',
    displayName: 'Apple',
    logoPath: '/attached_assets/logos/apple.svg',
    primaryColor: '#000000',
    secondaryColor: '#A8A8A8',
  },
  amazon: {
    id: 'amazon',
    name: 'Amazon',
    displayName: 'Amazon',
    logoPath: '/attached_assets/logos/amazon.svg',
    primaryColor: '#FF9900',
    secondaryColor: '#232F3E',
  },
  meta: {
    id: 'meta',
    name: 'Meta',
    displayName: 'Meta',
    logoPath: '/attached_assets/logos/meta.svg',
    primaryColor: '#1877F2',
    secondaryColor: '#42B883',
  },
  netflix: {
    id: 'netflix',
    name: 'Netflix',
    displayName: 'Netflix',
    logoPath: '/attached_assets/logos/netflix.svg',
    primaryColor: '#E50914',
    secondaryColor: '#221F1F',
  },
  stripe: {
    id: 'stripe',
    name: 'Stripe',
    displayName: 'Stripe',
    logoPath: '/attached_assets/logos/stripe.svg',
    primaryColor: '#635BFF',
    secondaryColor: '#0A2540',
  },
};

/**
 * Gets company info by exact name match (case insensitive)
 */
export function getCompanyInfo(companyName: string): CompanyInfo | null {
  if (!companyName) return null;
  
  const normalizedName = companyName.toLowerCase().trim();
  
  // Try exact match first
  if (COMPANY_LOGOS[normalizedName]) {
    return COMPANY_LOGOS[normalizedName];
  }
  
  // Try fuzzy matching
  for (const [key, company] of Object.entries(COMPANY_LOGOS)) {
    if (company.name.toLowerCase() === normalizedName || 
        company.displayName.toLowerCase() === normalizedName) {
      return company;
    }
  }
  
  return null;
}

/**
 * Gets company info by ID
 */
export function getCompanyById(id: string): CompanyInfo | null {
  return COMPANY_LOGOS[id.toLowerCase()] || null;
}

/**
 * Generates a company ID from a company name
 */
export function generateCompanyId(companyName: string): string {
  return companyName.toLowerCase()
    .replace(/\s+/g, '')
    .replace(/[^a-z0-9]/g, '');
}

/**
 * Gets all available companies
 */
export function getAllCompanies(): CompanyInfo[] {
  return Object.values(COMPANY_LOGOS);
}

/**
 * Checks if a company logo exists
 */
export function hasCompanyLogo(companyName: string): boolean {
  return getCompanyInfo(companyName) !== null;
}