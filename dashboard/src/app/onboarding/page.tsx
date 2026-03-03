"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { api } from "../../lib/api";

export default function OnboardingPage() {
  const session = useSession();
  const token = (session?.data as any)?.accessToken;

  const [status, setStatus] = useState<{ completed: boolean } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    api
      .getWizardStatus(token)
      .then((r) => setStatus(r))
      .catch((e) => setError(e?.message || String(e)))
      .finally(() => setLoading(false));
  }, [token]);

  if (!session || session.status === "loading" || loading) {
    return <div className="p-6">Loading...</div>;
  }
  if (error) return <div className="p-6 text-red-600">{error}</div>;

  if (status && !status.completed) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Onboarding</h1>
        <p>This server hasn't completed setup. Follow the wizard to configure SparkSage.</p>
        <a href="/wizard" className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded">Open Wizard</a>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Onboarding</h1>
      <p>Setup complete. Use the dashboard to adjust settings.</p>
    </div>
  );
}