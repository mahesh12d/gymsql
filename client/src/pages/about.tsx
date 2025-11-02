import LegalLayout from "@/components/legal-layout";
import aboutContent from "@/data/legal/about.md?raw";

export default function AboutPage() {
  return (
    <LegalLayout
      title="About GymSql"
      description="Learn about GymSql's mission to help you master SQL through practical, hands-on learning."
      content={aboutContent}
    />
  );
}
