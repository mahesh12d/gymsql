/**
 * Company Logo Mapping System
 * Maps company names to their corresponding SVG logos with unique IDs
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
  // Tech Giants
  microsoft: {
    id: 'microsoft',
    name: 'Microsoft',
    displayName: 'Microsoft',
    logoPath: '@assets/logos/microsoft.svg',
    primaryColor: '#00BCF2',
    secondaryColor: '#0078D4',
  },
  google: {
    id: 'google',
    name: 'Google',
    displayName: 'Google',
    logoPath: '@assets/logos/google.svg',
    primaryColor: '#4285F4',
    secondaryColor: '#DB4437',
  },
  apple: {
    id: 'apple',
    name: 'Apple',
    displayName: 'Apple',
    logoPath: '@assets/logos/apple.svg',
    primaryColor: '#000000',
    secondaryColor: '#A8A8A8',
  },
  amazon: {
    id: 'amazon',
    name: 'Amazon',
    displayName: 'Amazon',
    logoPath: '@assets/logos/amazon.svg',
    primaryColor: '#FF9900',
    secondaryColor: '#232F3E',
  },
  meta: {
    id: 'meta',
    name: 'Meta',
    displayName: 'Meta',
    logoPath: '@assets/logos/meta.svg',
    primaryColor: '#1877F2',
    secondaryColor: '#42B883',
  },
  facebook: {
    id: 'facebook',
    name: 'Facebook',
    displayName: 'Facebook',
    logoPath: '@assets/logos/facebook.svg',
    primaryColor: '#1877F2',
    secondaryColor: '#42B883',
  },
  
  // Cloud Providers
  aws: {
    id: 'aws',
    name: 'AWS',
    displayName: 'Amazon Web Services',
    logoPath: '@assets/logos/aws.svg',
    primaryColor: '#FF9900',
    secondaryColor: '#232F3E',
  },
  azure: {
    id: 'azure',
    name: 'Azure',
    displayName: 'Microsoft Azure',
    logoPath: '@assets/logos/azure.svg',
    primaryColor: '#0078D4',
    secondaryColor: '#00BCF2',
  },
  gcp: {
    id: 'gcp',
    name: 'GCP',
    displayName: 'Google Cloud Platform',
    logoPath: '@assets/logos/gcp.svg',
    primaryColor: '#4285F4',
    secondaryColor: '#DB4437',
  },
  
  // Financial Services
  jpmorgan: {
    id: 'jpmorgan',
    name: 'JPMorgan',
    displayName: 'JPMorgan Chase',
    logoPath: '@assets/logos/jpmorgan.svg',
    primaryColor: '#0066B2',
    secondaryColor: '#003C71',
  },
  goldman: {
    id: 'goldman',
    name: 'Goldman Sachs',
    displayName: 'Goldman Sachs',
    logoPath: '@assets/logos/goldman.svg',
    primaryColor: '#1E3A5F',
    secondaryColor: '#A8B5C8',
  },
  stripe: {
    id: 'stripe',
    name: 'Stripe',
    displayName: 'Stripe',
    logoPath: '@assets/logos/stripe.svg',
    primaryColor: '#635BFF',
    secondaryColor: '#0A2540',
  },
  
  // E-commerce & Retail
  shopify: {
    id: 'shopify',
    name: 'Shopify',
    displayName: 'Shopify',
    logoPath: '@assets/logos/shopify.svg',
    primaryColor: '#96BF48',
    secondaryColor: '#5E8E3E',
  },
  ebay: {
    id: 'ebay',
    name: 'eBay',
    displayName: 'eBay',
    logoPath: '@assets/logos/ebay.svg',
    primaryColor: '#E53238',
    secondaryColor: '#0064D2',
  },
  
  // Media & Entertainment
  netflix: {
    id: 'netflix',
    name: 'Netflix',
    displayName: 'Netflix',
    logoPath: '@assets/logos/netflix.svg',
    primaryColor: '#E50914',
    secondaryColor: '#221F1F',
  },
  spotify: {
    id: 'spotify',
    name: 'Spotify',
    displayName: 'Spotify',
    logoPath: '@assets/logos/spotify.svg',
    primaryColor: '#1DB954',
    secondaryColor: '#191414',
  },
  youtube: {
    id: 'youtube',
    name: 'YouTube',
    displayName: 'YouTube',
    logoPath: '@assets/logos/youtube.svg',
    primaryColor: '#FF0000',
    secondaryColor: '#CC0000',
  },
  
  // Social & Communication
  twitter: {
    id: 'twitter',
    name: 'Twitter',
    displayName: 'Twitter',
    logoPath: '@assets/logos/twitter.svg',
    primaryColor: '#1DA1F2',
    secondaryColor: '#14171A',
  },
  x: {
    id: 'x',
    name: 'X',
    displayName: 'X (Twitter)',
    logoPath: '@assets/logos/x.svg',
    primaryColor: '#000000',
    secondaryColor: '#536471',
  },
  linkedin: {
    id: 'linkedin',
    name: 'LinkedIn',
    displayName: 'LinkedIn',
    logoPath: '@assets/logos/linkedin.svg',
    primaryColor: '#0A66C2',
    secondaryColor: '#004182',
  },
  discord: {
    id: 'discord',
    name: 'Discord',
    displayName: 'Discord',
    logoPath: '@assets/logos/discord.svg',
    primaryColor: '#5865F2',
    secondaryColor: '#4752C4',
  },
  
  // Enterprise & Business
  salesforce: {
    id: 'salesforce',
    name: 'Salesforce',
    displayName: 'Salesforce',
    logoPath: '@assets/logos/salesforce.svg',
    primaryColor: '#00A1E0',
    secondaryColor: '#0176D3',
  },
  oracle: {
    id: 'oracle',
    name: 'Oracle',
    displayName: 'Oracle',
    logoPath: '@assets/logos/oracle.svg',
    primaryColor: '#F80000',
    secondaryColor: '#C74634',
  },
  ibm: {
    id: 'ibm',
    name: 'IBM',
    displayName: 'IBM',
    logoPath: '@assets/logos/ibm.svg',
    primaryColor: '#1261FE',
    secondaryColor: '#000000',
  },
  
  // Other Notable Companies
  uber: {
    id: 'uber',
    name: 'Uber',
    displayName: 'Uber',
    logoPath: '@assets/logos/uber.svg',
    primaryColor: '#000000',
    secondaryColor: '#5FB709',
  },
  airbnb: {
    id: 'airbnb',
    name: 'Airbnb',
    displayName: 'Airbnb',
    logoPath: '@assets/logos/airbnb.svg',
    primaryColor: '#FF5A5F',
    secondaryColor: '#00A699',
  },
  tesla: {
    id: 'tesla',
    name: 'Tesla',
    displayName: 'Tesla',
    logoPath: '@assets/logos/tesla.svg',
    primaryColor: '#CC0000',
    secondaryColor: '#000000',
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