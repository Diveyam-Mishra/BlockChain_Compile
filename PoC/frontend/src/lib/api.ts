export const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 20000);
  try {
    const url = `${BASE_URL}${path}`;
    const method = (init?.method || 'GET').toUpperCase();
    try {
      const bodyPreview = init?.body ? (typeof init.body === 'string' ? `${init.body.length}b` : 'body') : '—';
      // eslint-disable-next-line no-console
      console.debug('[api] request', { method, path, url, body: bodyPreview });
    } catch {}

    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
      signal: controller.signal,
      ...init,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      // eslint-disable-next-line no-console
      console.error('[api] response error', { method, path, status: res.status, statusText: res.statusText, body: text.slice(0, 500) });
      throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ''}`);
    }
    const ct = res.headers.get('content-type') || '';
    const out = (ct.includes('application/json') ? (await res.json()) : (await res.text())) as T;
    try {
      // eslint-disable-next-line no-console
      console.debug('[api] response ok', { method, path, status: res.status, ct });
    } catch {}
    return out;
  } finally {
    clearTimeout(id);
  }
}

async function reqForm<T>(path: string, form: FormData, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 30000);
  try {
    const url = `${BASE_URL}${path}`;
    try {
      // eslint-disable-next-line no-console
      console.debug('[api] request(form)', { method: 'POST', path, url });
    } catch {}
    const res = await fetch(url, {
      method: 'POST',
      body: form,
      signal: controller.signal,
      ...(init || {}),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      // eslint-disable-next-line no-console
      console.error('[api] response error(form)', { path, status: res.status, statusText: res.statusText, body: text.slice(0, 500) });
      throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ''}`);
    }
    try {
      // eslint-disable-next-line no-console
      console.debug('[api] response ok(form)', { path, status: res.status });
    } catch {}
    return (await res.json()) as T;
  } finally {
    clearTimeout(id);
  }
}

// Auditor endpoints
export const auditorApi = {
  status: (artifactHash: string) => req<{ artifact_hash: string; registry_app_id: number; status_code: number; status: string }>(`/api/v1/auditor/status/${artifactHash}`),
  reports: (artifactHash: string) => req<any>(`/api/v1/auditor/reports/${artifactHash}`),
  attest: (body: { artifact_hash: string; auditor_id?: string; statement: string; evidence_url?: string; status?: string }) =>
    req<{ status: string; attestation: any }>(`/api/v1/auditor/attestations`, { method: 'POST', body: JSON.stringify(body) }),
  listAttestations: (artifactHash: string) => req<{ artifact_hash: string; count: number; items: any[] }>(`/api/v1/auditor/attestations/${artifactHash}`),
};

// Controls endpoints
export const controlsApi = {
  families: () => req<string[]>(`/api/v1/controls/families`),
  list: (query = '', family = '', page = 1, limit = 10) => req<any>(`/api/v1/controls?query=${encodeURIComponent(query)}&family=${encodeURIComponent(family)}&page=${page}&limit=${limit}`),
  recommend: (artifact_text: string, limit = 5) => req<any>(`/api/v1/controls/recommend`, { method: 'POST', body: JSON.stringify({ artifact_text, limit }) }),
};

// IPFS endpoints
export const ipfsApi = {
  resolve: (cid: string) => req<{ cid: string; url: string; alt_url: string }>(`/api/v1/ipfs/resolve/${cid}`),
};

// Artifacts endpoints
export const artifactsApi = {
  upload: (file: File, description?: string) => {
    const fd = new FormData();
    fd.append('file', file);
    if (description) fd.append('description', description);
    return reqForm<{ artifact_id: string; artifact_hash: string; type: string; status: string; filename: string; dependencies_count: number }>(
      `/api/v1/artifacts/upload`,
      fd
    );
  },
  list: () => req<{ artifacts: any[]; count: number }>(`/api/v1/artifacts/`),
  profiles: () => req<{ profiles: { id: string; name: string; description: string; controls_count: number }[] }>(`/api/v1/artifacts/profiles`),
};

// Verification endpoints
export const verificationApi = {
  submit: (artifact_id: string, profile_id: string, wallet_address: string) => {
    const fd = new FormData();
    fd.append('artifact_id', artifact_id);
    fd.append('profile_id', profile_id);
    fd.append('wallet_address', wallet_address);
    return reqForm<any>(`/api/v1/verification/submit`, fd);
  },
  status: (artifact_hash: string) => req<any>(`/api/v1/verification/status/${artifact_hash}`),
  reports: (artifact_hash: string) => req<any>(`/api/v1/verification/reports/${artifact_hash}`),
};
