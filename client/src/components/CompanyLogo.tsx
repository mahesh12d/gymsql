import { useEffect, useState } from "react";
import { Building2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { getCompanyLogo, CompanyInfo } from "@/data/companyLogos";

interface CompanyLogoProps {
  companyName: string | null | undefined;
  variant?: "badge" | "icon" | "full" | "minimal";
  size?: "sm" | "md" | "lg";
  showFallback?: boolean;
  className?: string;
  onClick?: () => void;
  "data-testid"?: string;
}

/**
 * CompanyLogo component that displays SVG logos based on company names
 * with fallback support and multiple display variants
 */
export function CompanyLogo({
  companyName,
  variant = "badge",
  size = "md",
  showFallback = true,
  className = "",
  onClick,
  "data-testid": testId,
}: CompanyLogoProps) {
  const [companyInfo, setCompanyInfo] = useState<CompanyInfo | null>(null);
  const [logoSrc, setLogoSrc] = useState<string | null>(null);
  const [logoError, setLogoError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!companyName) {
      setCompanyInfo(null);
      setLogoSrc(null);
      setLogoError(false);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setLogoError(false);
    
    try {
      const info = getCompanyLogo(companyName);
      setCompanyInfo(info);

      if (info) {
        setLogoSrc(info.logoPath);
      } else {
        setLogoSrc(null);
      }
    } catch (error) {
      console.error('Error loading company info:', error);
      setCompanyInfo(null);
      setLogoSrc(null);
      setLogoError(true);
    } finally {
      setIsLoading(false);
    }
  }, [companyName]);

  // Size configurations
  const sizeConfig = {
    sm: {
      logo: "w-3 h-3",
      badge: "text-xs px-2 py-1",
      icon: "w-4 h-4",
      text: "text-xs",
    },
    md: {
      logo: "w-4 h-4",
      badge: "text-xs px-2 py-1",
      icon: "w-5 h-5",
      text: "text-sm",
    },
    lg: {
      logo: "w-6 h-6",
      badge: "text-sm px-3 py-1.5",
      icon: "w-6 h-6",
      text: "text-base",
    },
  };

  const config = sizeConfig[size];

  // Handle logo loading error
  const handleLogoError = () => {
    setLogoError(true);
  };

  // If no company name and no fallback, return null
  if (!companyName && !showFallback) {
    return null;
  }

  // If no company name but fallback is enabled
  if (!companyName && showFallback) {
    return (
      <span className={`text-gray-400 ${config.text} ${className}`} data-testid={testId}>
        -
      </span>
    );
  }

  // Render based on variant
  switch (variant) {
    case "icon":
      return (
        <div 
          className={`flex items-center justify-center ${config.icon} ${className}`}
          onClick={onClick}
          data-testid={testId}
          style={{ 
            color: companyInfo?.primaryColor || "#6B7280",
            cursor: onClick ? "pointer" : "default"
          }}
        >
          {logoSrc && !logoError ? (
            <img
              src={logoSrc}
              alt={`${companyName} logo`}
              className={`${config.logo} object-contain`}
              onError={handleLogoError}
              style={{ 
                filter: companyInfo ? 'none' : 'grayscale(100%)',
              }}
            />
          ) : (
            <Building2 className={config.icon} />
          )}
        </div>
      );

    case "minimal":
      return (
        <div 
          className={`inline-flex items-center gap-1.5 ${className}`}
          onClick={onClick}
          data-testid={testId}
          style={{ cursor: onClick ? "pointer" : "default" }}
        >
          {logoSrc && !logoError ? (
            <img
              src={logoSrc}
              alt={`${companyName} logo`}
              className={`${config.logo} object-contain`}
              onError={handleLogoError}
            />
          ) : (
            <Building2 className={config.logo} style={{ color: companyInfo?.primaryColor || "#6B7280" }} />
          )}
          <span className={`${config.text} font-medium`} style={{ color: companyInfo?.primaryColor || "#374151" }}>
            {companyName}
          </span>
        </div>
      );

    case "full":
      return (
        <div
          className={`company-field ${companyInfo ? "selected" : ""} ${className}`}
          onClick={onClick}
          data-testid={testId}
          style={{
            backgroundColor: companyInfo?.primaryColor ? `${companyInfo.primaryColor}10` : undefined,
            borderColor: companyInfo?.primaryColor ? `${companyInfo.primaryColor}30` : undefined,
          }}
        >
          <span className="company-icon">
            {logoSrc && !logoError ? (
              <img
                src={logoSrc}
                alt={`${companyName} logo`}
                className="company-logo"
                onError={handleLogoError}
              />
            ) : (
              <Building2 className="w-3.5 h-3.5" style={{ color: companyInfo?.primaryColor || "#6B7280" }} />
            )}
          </span>
          <span className="company-name" style={{ color: companyInfo?.primaryColor || "#374151" }}>
            {companyInfo?.displayName || companyName}
          </span>
          <span className={`selected-dot ${companyInfo ? "visible" : ""}`} />
        </div>
      );

    case "badge":
    default:
      return (
        <Badge
          variant="outline"
          className={`bg-blue-50 text-blue-700 border-blue-200 ${config.badge} flex items-center gap-1.5 ${className}`}
          onClick={onClick}
          data-testid={testId}
          style={{
            backgroundColor: companyInfo?.primaryColor ? `${companyInfo.primaryColor}15` : undefined,
            borderColor: companyInfo?.primaryColor ? `${companyInfo.primaryColor}40` : undefined,
            color: companyInfo?.primaryColor || "#1D4ED8",
            cursor: onClick ? "pointer" : "default"
          }}
        >
          {logoSrc && !logoError ? (
            <img
              src={logoSrc}
              alt={`${companyName} logo`}
              className={`${config.logo} object-contain`}
              onError={handleLogoError}
            />
          ) : (
            <Building2 className={config.logo} />
          )}
          {companyInfo?.displayName || companyName}
        </Badge>
      );
  }
}

/**
 * Simplified component for backward compatibility
 */
export function CompanyBadge({ companyName, className, ...props }: Omit<CompanyLogoProps, "variant">) {
  return (
    <CompanyLogo
      companyName={companyName}
      variant="badge"
      className={className}
      {...props}
    />
  );
}

export default CompanyLogo;