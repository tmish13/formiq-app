import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';

export default function TermsPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      <div className="max-w-2xl mx-auto px-6 py-10">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(-1)}
          className="mb-6 -ml-2"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>

        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Terms of Service</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-10">Effective: January 1, 2026</p>

        <div className="prose prose-gray dark:prose-invert max-w-none space-y-8 text-gray-700 dark:text-gray-300">

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">1. Acceptance of Terms</h2>
            <p className="text-sm leading-relaxed">
              By accessing or using FormIQ ("Service"), you agree to be bound by these Terms of Service. If you
              do not agree to these terms, do not use the Service. FormIQ reserves the right to update these
              terms at any time; continued use after changes constitutes acceptance.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">2. Beta Service Disclaimer</h2>
            <p className="text-sm leading-relaxed">
              FormIQ is currently in beta. The Service is provided on an "as-is" and "as-available" basis
              without warranties of any kind, express or implied. AI-generated form analysis is for
              informational purposes only and is not a substitute for professional instruction or medical
              advice. Scores and feedback may not be accurate in all cases.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">3. User Responsibilities</h2>
            <p className="text-sm leading-relaxed mb-3">You agree to:</p>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              <li>Provide accurate account information and keep it up to date.</li>
              <li>Maintain the security of your login credentials.</li>
              <li>Use the Service only for lawful personal fitness purposes.</li>
              <li>Upload only videos of yourself performing exercises.</li>
              <li>Not share your account with others.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">4. Content and Video Usage</h2>
            <p className="text-sm leading-relaxed">
              You retain ownership of videos you upload. By uploading, you grant FormIQ a limited,
              non-exclusive license to process and analyze your videos solely to provide the Service. Videos
              are used for AI-powered form analysis and are not shared with third parties for marketing
              purposes. Refer to our Privacy Policy for details on data handling and retention.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">5. Prohibited Misuse</h2>
            <p className="text-sm leading-relaxed mb-3">You may not:</p>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              <li>Upload content that depicts others without their consent.</li>
              <li>Attempt to reverse-engineer or scrape the Service.</li>
              <li>Use the Service to train competing AI systems.</li>
              <li>Circumvent security measures or access controls.</li>
              <li>Upload any illegal, harmful, or offensive content.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">6. Limitation of Liability</h2>
            <p className="text-sm leading-relaxed">
              To the fullest extent permitted by law, FormIQ shall not be liable for any indirect, incidental,
              special, or consequential damages arising from use of or inability to use the Service, including
              any injuries arising from following AI-generated feedback.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">7. Contact</h2>
            <p className="text-sm leading-relaxed">
              Questions about these Terms? Contact us at{' '}
              <a
                href="mailto:support@formiq.app"
                className="text-indigo-600 dark:text-indigo-400 underline"
              >
                support@formiq.app
              </a>
              .
            </p>
          </section>
        </div>

        <p className="mt-12 text-xs text-gray-400 dark:text-gray-500">
          © {new Date().getFullYear()} FormIQ. All rights reserved.
        </p>
      </div>
    </div>
  );
}
