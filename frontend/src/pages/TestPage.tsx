import React from 'react';

export default function TestPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">FormIQ Test Page</h1>
        <p className="text-gray-600 mb-4">
          If you can see this page with proper styling, the basic setup is working correctly.
        </p>
        <div className="space-y-2">
          <p className="text-sm text-gray-500">✅ React is working</p>
          <p className="text-sm text-gray-500">✅ Tailwind CSS is working</p>
          <p className="text-sm text-gray-500">✅ Routing is working</p>
        </div>
        <button 
          onClick={() => window.location.href = '/auth'}
          className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
        >
          Go to Auth Page
        </button>
      </div>
    </div>
  );
}