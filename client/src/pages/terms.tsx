import LegalLayout from "@/components/legal-layout";
import termsContent from "@/data/legal/terms.md?raw";

export default function TermsPage() {
  return (
    <LegalLayout
      title="Terms and Conditions"
      description="Read GymSql's Terms and Conditions governing the use of our SQL training platform."
      content={termsContent}
    />
  );
}
