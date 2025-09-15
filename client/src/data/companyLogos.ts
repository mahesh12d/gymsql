/**
 * Dynamic Company Logo System
 * Automatically loads company logos based on SVG filename matching company name
 * Just add {companyname}.svg to attached_assets/logos/ and it will work automatically
 */

export interface CompanyInfo {
  id: string;
  name: string;
  displayName: string;
  logoPath: string;
  primaryColor: string;
  secondaryColor?: string;
}

// Default color configurations for known companies
// These are optional - if not defined, fallback colors will be used
const COMPANY_COLORS: Record<string, Pick<CompanyInfo, 'primaryColor' | 'secondaryColor'>> = {
  microsoft: {
    primaryColor: '#00BCF2',
    secondaryColor: '#0078D4',
  },
  google: {
    primaryColor: '#4285F4',
    secondaryColor: '#DB4437',
  },
  apple: {
    primaryColor: '#000000',
    secondaryColor: '#A8A8A8',
  },
  amazon: {
    primaryColor: '#FF9900',
    secondaryColor: '#232F3E',
  },
  meta: {
    primaryColor: '#1877F2',
    secondaryColor: '#42B883',
  },
  netflix: {
    primaryColor: '#E50914',
    secondaryColor: '#221F1F',
  },
  stripe: {
    primaryColor: '#635BFF',
    secondaryColor: '#0A2540',
  },
  airbnb: {
    primaryColor: '#FF5A5F',
    secondaryColor: '#FF385C',
  },
};

// Cache for loaded logos to avoid repeated dynamic imports
const logoCache = new Map<string, string>();

/**
 * Dynamically loads a company logo based on company name
 * Expects logo file to be named {companyname}.svg in attached_assets/logos/
 */
async function loadCompanyLogo(companyName: string): Promise<string | null> {
  const normalizedName = normalizeCompanyName(companyName);
  
  // Check cache first
  if (logoCache.has(normalizedName)) {
    return logoCache.get(normalizedName)!;
  }
  
  try {
    // Try to dynamically import the logo
    const logoModule = await import(`@assets/logos/${normalizedName}.svg`);
    const logoPath = logoModule.default;
    
    // Cache the result
    logoCache.set(normalizedName, logoPath);
    return logoPath;
  } catch (error) {
    // Logo doesn't exist, cache null to avoid repeated attempts
    logoCache.set(normalizedName, '');
    return null;
  }
}

/**
 * Normalizes company name to match expected filename format
 */
function normalizeCompanyName(companyName: string): string {
  return companyName.toLowerCase()
    .trim()
    .replace(/\s+/g, '')
    .replace(/[^a-z0-9]/g, '');
}

/**
 * Gets company info by name, dynamically loading logo if available
 */
export async function getCompanyInfo(companyName: string): Promise<CompanyInfo | null> {
  if (!companyName) return null;
  
  const normalizedName = normalizeCompanyName(companyName);
  const logoPath = await loadCompanyLogo(companyName);
  
  // If no logo found, return null
  if (!logoPath) return null;
  
  // Get colors from config or use defaults
  const colors = COMPANY_COLORS[normalizedName] || {
    primaryColor: '#6366F1', // Default indigo
    secondaryColor: '#4F46E5',
  };
  
  // Create display name (capitalize first letter of each word)
  const displayName = companyName
    .toLowerCase()
    .split(/\s+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
  
  return {
    id: normalizedName,
    name: displayName,
    displayName: displayName,
    logoPath: logoPath,
    primaryColor: colors.primaryColor,
    secondaryColor: colors.secondaryColor,
  };
}

/**
 * Synchronous version for cases where logo path is already cached
 */
export function getCompanyInfoSync(companyName: string): CompanyInfo | null {
  if (!companyName) return null;
  
  const normalizedName = normalizeCompanyName(companyName);
  const cachedLogo = logoCache.get(normalizedName);
  
  // If not in cache or cached as empty, return null
  if (!cachedLogo) return null;
  
  // Get colors from config or use defaults
  const colors = COMPANY_COLORS[normalizedName] || {
    primaryColor: '#6366F1', // Default indigo
    secondaryColor: '#4F46E5',
  };
  
  // Create display name
  const displayName = companyName
    .toLowerCase()
    .split(/\s+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
  
  return {
    id: normalizedName,
    name: displayName,
    displayName: displayName,
    logoPath: cachedLogo,
    primaryColor: colors.primaryColor,
    secondaryColor: colors.secondaryColor,
  };
}

/**
 * Gets company info by ID
 */
export async function getCompanyById(id: string): Promise<CompanyInfo | null> {
  return await getCompanyInfo(id);
}

/**
 * Generates a company ID from a company name
 */
export function generateCompanyId(companyName: string): string {
  return normalizeCompanyName(companyName);
}

/**
 * Gets all available companies (only those with cached logos)
 */
export function getAllCompanies(): CompanyInfo[] {
  const companies: CompanyInfo[] = [];
  
  for (const [normalizedName, logoPath] of logoCache.entries()) {
    if (logoPath) { // Only include companies with valid logos
      const colors = COMPANY_COLORS[normalizedName] || {
        primaryColor: '#6366F1',
        secondaryColor: '#4F46E5',
      };
      
      const displayName = normalizedName.charAt(0).toUpperCase() + normalizedName.slice(1);
      
      companies.push({
        id: normalizedName,
        name: displayName,
        displayName: displayName,
        logoPath: logoPath,
        primaryColor: colors.primaryColor,
        secondaryColor: colors.secondaryColor,
      });
    }
  }
  
  return companies;
}

/**
 * Checks if a company logo exists (async version)
 */
export async function hasCompanyLogo(companyName: string): Promise<boolean> {
  const info = await getCompanyInfo(companyName);
  return info !== null;
}