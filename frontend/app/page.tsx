"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";

export default function Home() {
  const [status, setStatus] = useState<string>("checking…");

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((d) => setStatus(d.status ?? "unknown"))
      .catch(() => setStatus("backend unreachable"));
  }, []);

  return (
    <main className="mx-auto max-w-xl px-4 py-10">
      <h1 className="text-2xl font-bold">PF Sahay</h1>
      <p className="mt-2 text-sm text-gray-600">
        Diagnose a rejected EPF claim and get the documents to fix it.
      </p>
      <p className="mt-6">
        Backend status: <span data-testid="health" className="font-mono font-semibold">{status}</span>
      </p>
    </main>
  );
}
