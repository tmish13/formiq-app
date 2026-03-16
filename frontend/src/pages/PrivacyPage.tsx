import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';

export default function PrivacyPage() {
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

        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Privacy Policy</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-10">Effective: January 1, 2026</p>

        <div className="prose prose-gray dark:prose-invert max-w-none space-y-8 text-gray-700 dark:text-gray-300">

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">1. Data We Collect</h2>
            <p className="text-sm leading-relaxed mb-3">When you use FormIQ, we collect:</p>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              <li><strong>Account information</strong> — email address, name, and password (stored as a secure hash).</li>
              <li><strong>Exercise videos</strong> — videos you upload for form analysis.</li>
              <li><strong>Fitness preferences</strong> — fitness goals and preferred exercises you provide during onboarding.</li>
              <li><strong>Usage data</strong> — feature interactions and session activity to improve the Service.</li>
              <li><strong>Device information</strong> — browser type, operating system, and IP address for security and debugging.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">2. Uploaded Video Handling</h2>
            <p className="text-sm leading-relaxed">
              Videos you upload are stored securely on Amazon Web Services (AWS S3) and are processed by
              our AI pipeline to extract pose data (body landmark coordinates). The pose data — not the raw
              video — is what drives analysis results. Videos are associated only with your account and are
              not accessible to other users or shared for advertising purposes.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">3. Account and Authentication Data</h2>
            <p className="text-sm leading-relaxed">
              Passwords are hashed using industry-standard cryptographic algorithms and are never stored in
              plain text. Authentication tokens are short-lived and stored in your browser's local storage.
              We use email for account verification and important service communications only.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">4. Analytics and Logging</h2>
            <p className="text-sm leading-relaxed">
              FormIQ collects anonymized usage metrics (e.g., features used, error rates) to improve the
              product. Client-side events are logged locally in your browser and may be sent to our backend
              for diagnostics. We do not use third-party advertising trackers.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">5. Data Sharing</h2>
            <p className="text-sm leading-relaxed">
              We do not sell, rent, or share your personal data or videos with third parties for commercial
              purposes. Data may be shared with service providers (e.g., AWS for storage, infrastructure
              providers) strictly to operate the Service. We may disclose data if required by law.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">6. Data Retention and Deletion</h2>
            <p className="text-sm leading-relaxed">
              Your account data and uploaded videos are retained while your account is active. You may request
              deletion of your account and all associated data by contacting us. Upon deletion, your data will
              be removed from our active systems within 30 days, subject to legal retention obligations.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">7. Contact</h2>
            <p className="text-sm leading-relaxed">
              For privacy questions or data requests, contact us at{' '}
              <a
                href="mailto:privacy@formiq.app"
                className="text-indigo-600 dark:text-indigo-400 underline"
              >
                privacy@formiq.app
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
