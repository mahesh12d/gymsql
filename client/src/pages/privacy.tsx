import LegalLayout from "@/components/legal-layout";
import privacyContent from "@/data/legal/privacy.md?raw";

export default function PrivacyPage() {
  return (
    <LegalLayout
      title="Privacy Policy"
      description="Learn how SQLGym collects, uses, and protects your personal information."
      content={privacyContent}
    />
  );
}
