import React, { useEffect, useRef, useState } from 'react';
import { Upload, Shield, FileCheck, Download, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { artifactsApi, verificationApi } from '@/lib/api';
import OnChainLinks from '@/components/OnChainLinks';

const CompanyPortal = () => {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [artifactHash, setArtifactHash] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<{ id: string; name: string }[]>([]);
  const [complianceStandard, setComplianceStandard] = useState('');
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [complianceScore, setComplianceScore] = useState<number | null>(null);
  const [verificationStatus, setVerificationStatus] = useState<'pending' | 'verified' | 'failed' | null>(null);
  const [statusData, setStatusData] = useState<any | null>(null);
  const pollingRef = useRef<number | null>(null);
  const [shouldPoll, setShouldPoll] = useState(false);
  const { toast } = useToast();
  const [pasteJson, setPasteJson] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'file' | 'paste'>('file');
  // Findings state
  const [findings, setFindings] = useState<any[]>([]);
  const [controlsPassed, setControlsPassed] = useState<number | null>(null);
  const [controlsFailed, setControlsFailed] = useState<number | null>(null);
  const [oscalLinks, setOscalLinks] = useState<null | {
    directory_cid: string;
    directory_url: string;
    component_definition: string;
    assessment_plan: string;
    assessment_results: string;
    poam: string;
  }>(null);

  useEffect(() => {
    // load profiles from backend
    artifactsApi
      .profiles()
      .then((res) => {
        const mapped = res.profiles.map((p: any) => ({ id: p.id, name: p.name }));
        try { console.debug('[ui] profiles loaded', { count: mapped.length, items: mapped }); } catch {}
        setProfiles(mapped);
      })
      .catch((e) => {
        try { console.error('[ui] profiles load failed', e); } catch {}
        setProfiles([]);
      });
  }, []);

  // Poll verification status until terminal
  useEffect(() => {
    if (!artifactHash || !shouldPoll) return;
    // Clear any existing interval
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    // Start polling with simple backoff based on attempts
    let attempts = 0;
    const tick = async () => {
      try {
        const s = await verificationApi.status(artifactHash);
        setStatusData(s);
        // Normalize status for badge
        const code = typeof s?.status_code === 'number' ? s.status_code : undefined;
        const text = (s?.status || '').toString().toLowerCase();
        if (code === 1 || text.includes('verified') || text.includes('success')) {
          setVerificationStatus('verified');
        } else if (code === 2 || text.includes('fail')) {
          setVerificationStatus('failed');
        } else {
          setVerificationStatus('pending');
        }
        try { console.debug('[ui] status poll', { artifactHash, code, text: s?.status, statusData: s }); } catch {}
        // When terminal, stop polling and load findings/reports
        if (verificationStatus === 'verified' || verificationStatus === 'failed' || code === 1 || code === 2) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          setShouldPoll(false);
          try { await loadFindings(artifactHash); } catch (err) { try { console.error('[ui] loadFindings after terminal failed', err); } catch {} }
          return;
        }
      } catch {
        // ignore transient status errors
      }
      // backoff: first 3 polls @3s, then @8s while pending
      attempts += 1;
      const delay = attempts <= 3 ? 3000 : 8000;
      pollingRef.current = window.setTimeout(tick, delay);
    };
    // kick off first tick immediately
    tick();
    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [artifactHash, shouldPoll]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      try {
        try { console.debug('[ui] file selected', { name: file.name, size: file.size, type: file.type }); } catch {}
        const res = await artifactsApi.upload(file);
        setArtifactId(res.artifact_id);
        setArtifactHash(res.artifact_hash);
        try { console.debug('[ui] upload success', { artifact_id: res.artifact_id, artifact_hash: res.artifact_hash, filename: res.filename, type: res.type }); } catch {}
        toast({ title: 'Artifact parsed', description: `${res.filename} • ${res.type}` });
      } catch (e: any) {
        try { console.error('[ui] upload failed', e); } catch {}
        toast({ title: 'Upload failed', description: String(e), variant: 'destructive' });
      }
    }
  };

  const handlePasteUpload = async () => {
    try {
      if (!pasteJson.trim()) {
        toast({ title: 'Empty input', description: 'Paste a valid SBOM JSON first', variant: 'destructive' });
        return;
      }
      // Validate JSON
      const obj = JSON.parse(pasteJson);
      try { console.debug('[ui] paste validated', { size: pasteJson.length, keys: Object.keys(obj).slice(0, 10) }); } catch {}
      const jsonStr = JSON.stringify(obj);
      const file = new File([jsonStr], 'pasted-sbom.json', { type: 'application/json' });
      setUploadedFile(file);
      const res = await artifactsApi.upload(file);
      setArtifactId(res.artifact_id);
      setArtifactHash(res.artifact_hash);
      try { console.debug('[ui] paste upload success', { artifact_id: res.artifact_id, artifact_hash: res.artifact_hash }); } catch {}
      toast({ title: 'Artifact parsed (pasted JSON)', description: `${res.filename} • ${res.type}` });
    } catch (e: any) {
      try { console.error('[ui] paste upload failed', e); } catch {}
      toast({ title: 'Invalid JSON or upload failed', description: String(e), variant: 'destructive' });
    }
  };

  const startAnalysis = async () => {
    if (!artifactId || !complianceStandard) {
      toast({
        title: "Missing requirements",
        description: "Please upload and parse an artifact, and select a profile",
        variant: "destructive",
      });
      return;
    }

    setIsAnalyzing(true);
    setAnalysisProgress(0);
    
    try {
      // kick off full pipeline by artifact id
      try { console.debug('[ui] startAnalysis', { artifactId, profile: complianceStandard }); } catch {}
      const res = await verificationApi.submitByArtifact(artifactId, complianceStandard);
      setAnalysisProgress(100);
      setIsAnalyzing(false);
      // Keep UI in pending and start polling until terminal
      setVerificationStatus('pending');
      if (res.artifact_hash) setArtifactHash(res.artifact_hash);
      setShouldPoll(true);
      try { console.debug('[ui] verification started', { response: res }); } catch {}
      toast({ title: 'Verification started', description: 'Processing: AI → IPFS → Algorand. Status will update automatically.' });
    } catch (e: any) {
      setIsAnalyzing(false);
      setVerificationStatus('failed');
      try { console.error('[ui] startAnalysis failed', e); } catch {}
      toast({ title: 'Verification failed', description: String(e), variant: 'destructive' });
    }
  };

  const loadFindings = async (hash?: string | null) => {
    const h = hash || artifactHash;
    if (!h) return;
    try {
      try { console.debug('[ui] loadFindings begin', { artifactHash: h }); } catch {}
      const reports = await verificationApi.reports(h);
      const links = (reports && (reports.verified || reports.initial)) || null;
      if (!links) return;
      setOscalLinks(links);
      // Prefer assessment_results.json, fallback to directory root JSON
      let jsonUrl = links.assessment_results || links.directory_url;
      let data: any = null;
      try {
        const r = await fetch(jsonUrl);
        if (r.ok) {
          const ct = r.headers.get('content-type') || '';
          data = ct.includes('application/json') ? await r.json() : JSON.parse(await r.text());
        }
      } catch (_) {
        // fallback attempt to directory URL if not already
        if (jsonUrl !== links.directory_url) {
          const r2 = await fetch(links.directory_url);
          if (r2.ok) {
            const ct2 = r2.headers.get('content-type') || '';
            data = ct2.includes('application/json') ? await r2.json() : JSON.parse(await r2.text());
          }
        }
      }
      if (!data) return;
      // Extract results flexibly
      const results = data.results || data;
      const f: any[] = Array.isArray(results.findings) ? results.findings : [];
      setFindings(f);
      if (typeof results.score === 'number') setComplianceScore(results.score);
      if (typeof results.controls_passed === 'number') setControlsPassed(results.controls_passed);
      if (typeof results.controls_failed === 'number') setControlsFailed(results.controls_failed);
      try { console.debug('[ui] loadFindings ok', { findings: f.length, score: results.score, passed: results.controls_passed, failed: results.controls_failed }); } catch {}
    } catch (err) {
      // Silent failure; user can still download via links
      try { console.error('[ui] loadFindings error', err); } catch {}
    }
  };

  const downloadOSCALReports = () => {
    if (!oscalLinks) {
      toast({ title: 'No reports yet', description: 'Reports will be available once verification completes', variant: 'destructive' });
      return;
    }
    const urls = [
      oscalLinks.component_definition,
      oscalLinks.assessment_plan,
      oscalLinks.assessment_results,
      oscalLinks.poam,
    ].filter(Boolean) as string[];
    if (urls.length === 0) {
      toast({ title: 'Links unavailable', description: 'OSCAL links not returned by backend yet', variant: 'destructive' });
      return;
    }
    try { console.debug('[ui] download OSCAL', { urls }); } catch {}
    urls.forEach((u) => window.open(u, '_blank', 'noopener,noreferrer'));
    toast({ title: 'Downloads opened', description: `${urls.length} OSCAL document(s)` });
  };

  const exportPdf = () => {
    try {
      const date = new Date().toLocaleString();
      const title = `CompliLedger Verification Report`;
      const oscalUrl = oscalLinks?.assessment_results || oscalLinks?.directory_url || '';
      const safe = (s: any) => (s == null ? '' : String(s));
      const topFindings = (findings || []).slice(0, 10);
      try { console.debug('[ui] export PDF', { findings: findings?.length || 0, score: complianceScore }); } catch {}
      const html = `<!doctype html>
  <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>${title}</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, 'Helvetica Neue', Arial, sans-serif; padding: 24px; color: #111827; }
        h1 { margin: 0 0 8px; font-size: 22px; }
        h2 { margin: 16px 0 8px; font-size: 16px; }
        .muted { color: #6b7280; font-size: 12px; }
        .section { margin-top: 16px; }
        .kpis { display: flex; gap: 16px; margin-top: 8px; }
        .kpi { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; min-width: 140px; }
        .kpi .value { font-size: 20px; font-weight: 700; }
        .kpi.pass { color: #10b981; }
        .kpi.fail { color: #ef4444; }
        .finding { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-top: 8px; }
        .sev { padding: 2px 8px; border-radius: 10px; font-size: 11px; border: 1px solid #e5e7eb; }
        .sev.high { background: #fee2e2; border-color: #fecaca; }
        .sev.medium { background: #fef9c3; border-color: #fde68a; }
        .sev.low { background: #dcfce7; border-color: #bbf7d0; }
        .controls { margin-top: 6px; color: #6b7280; font-size: 12px; }
        @media print { a { color: inherit; text-decoration: none; } }
      </style>
    </head>
    <body>
      <h1>${title}</h1>
      <div class="muted">Generated: ${safe(date)}</div>
      ${oscalUrl ? `<div class="muted">Verified OSCAL: ${oscalUrl}</div>` : ''}
      <div class="section">
        <h2>Summary</h2>
        <div class="kpis">
          <div class="kpi"><div class="label muted">Compliance Score</div><div class="value">${safe(complianceScore ?? '—')}%</div></div>
          <div class="kpi pass"><div class="label muted">Controls Passed</div><div class="value">${safe(controlsPassed ?? '—')}</div></div>
          <div class="kpi fail"><div class="label muted">Controls Failed</div><div class="value">${safe(controlsFailed ?? '—')}</div></div>
        </div>
      </div>
      <div class="section">
        <h2>Findings${topFindings.length ? ` (${topFindings.length}${findings.length > 10 ? '+' : ''})` : ''}</h2>
        ${topFindings
          .map((f: any, i: number) => {
            const sev = String(f?.severity || '').toLowerCase();
            const sevCls = sev.includes('high') ? 'high' : sev.includes('medium') ? 'medium' : 'low';
            const title = f?.title || f?.id || `Finding ${i + 1}`;
            const desc = f?.description || '';
            const tags = Array.isArray(f?.control_tags) ? f.control_tags : [];
            return `<div class="finding">
              <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;">
                <div style="font-weight:600;">${safe(title)}</div>
                ${sev ? `<span class="sev ${sevCls}">${safe(f.severity)}</span>` : ''}
              </div>
              ${desc ? `<div style="margin-top:6px; font-size:13px;">${safe(desc)}</div>` : ''}
              ${tags.length ? `<div class="controls">Controls: ${tags.map((t:any)=>`<code>${safe(t)}</code>`).join(', ')}</div>` : ''}
            </div>`;
          })
          .join('')}
      </div>
      <script>window.onload = () => { window.print(); };</script>
    </body>
  </html>`;

      const w = window.open('', '_blank', 'noopener,noreferrer');
      if (!w) throw new Error('Popup blocked');
      w.document.open();
      w.document.write(html);
      w.document.close();
    } catch (e) {
      toast({ title: 'Export failed', description: String(e), variant: 'destructive' });
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 cosmic-grid">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tighter text-foreground">
            CompliLedger Company Portal
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            AI-powered compliance verification with blockchain anchoring and OSCAL-standardized reporting
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Upload Section */}
          <Card className="cosmic-glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload Artifact
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'file' | 'paste')}>
                <TabsList className="grid grid-cols-2 w-full">
                  <TabsTrigger value="file">Upload File</TabsTrigger>
                  <TabsTrigger value="paste">Paste SBOM (JSON)</TabsTrigger>
                </TabsList>

                <TabsContent value="file" className="mt-4">
                  <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
                    <input
                      type="file"
                      id="file-upload"
                      className="hidden"
                      onChange={handleFileUpload}
                      accept=".json,.sol,.js,.ts,.py"
                    />
                    <label
                      htmlFor="file-upload"
                      className="cursor-pointer flex flex-col items-center space-y-2"
                    >
                      <Upload className="h-12 w-12 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">
                        Drop your SBOM or Smart Contract here, or click to browse
                      </span>
                      <span className="text-xs text-muted-foreground">
                        Supports: JSON, Solidity, JavaScript, TypeScript, Python
                      </span>
                    </label>
                  </div>
                </TabsContent>

                <TabsContent value="paste" className="mt-4">
                  <div className="space-y-3">
                    <Textarea
                      placeholder="Paste SBOM JSON here"
                      value={pasteJson}
                      onChange={(e) => setPasteJson(e.target.value)}
                      className="min-h-[200px] font-mono text-sm"
                    />
                    <div className="flex justify-end">
                      <Button onClick={handlePasteUpload} variant="secondary">Validate & Upload</Button>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>

              {uploadedFile && (
                <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                  <FileCheck className="h-4 w-4 text-green-500" />
                  <span className="text-sm">{uploadedFile.name}</span>
                  <Badge variant="secondary">{Math.round(uploadedFile.size / 1024)} KB</Badge>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium">Compliance Standard</label>
                <Select value={complianceStandard} onValueChange={(v) => { try { console.debug('[ui] select profile', { value: v }); } catch {}; setComplianceStandard(v); }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select compliance framework" />
                  </SelectTrigger>
                  <SelectContent>
                    {profiles.map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Button 
                onClick={startAnalysis} 
                disabled={!artifactId || !complianceStandard || isAnalyzing}
                className="w-full"
              >
                {isAnalyzing ? 'Processing...' : 'Start Verification'}
              </Button>
            </CardContent>
          </Card>

          {/* Results Section */}
          <Card className="cosmic-glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Verification Results
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {isAnalyzing && (
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span>Analysis Progress</span>
                    <span>{analysisProgress}%</span>
                  </div>
                  <Progress value={analysisProgress} className="h-2" />
                  <p className="text-xs text-muted-foreground">
                    AI is analyzing your artifact against {complianceStandard} controls...
                  </p>
                </div>
              )}

              {complianceScore !== null && (
                <div className="space-y-4">
                  <div className="text-center space-y-2">
                    <div className="text-3xl font-bold text-green-500">{complianceScore}%</div>
                    <p className="text-sm text-muted-foreground">Compliance Score</p>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div className="space-y-1">
                      <div className="text-2xl font-semibold text-green-500">{controlsPassed ?? '—'}</div>
                      <p className="text-xs text-muted-foreground">Controls Passed</p>
                    </div>
                    <div className="space-y-1">
                      <div className="text-2xl font-semibold text-red-500">{controlsFailed ?? '—'}</div>
                      <p className="text-xs text-muted-foreground">Controls Failed</p>
                    </div>
                  </div>

                  {verificationStatus && (
                    <div className={`flex items-center justify-center gap-2 p-3 rounded-lg border ${verificationStatus === 'verified' ? 'bg-green-500/10 border-green-500/20' : verificationStatus === 'failed' ? 'bg-red-500/10 border-red-500/20' : 'bg-amber-500/10 border-amber-500/20'}`}>
                      <Shield className={`h-4 w-4 ${verificationStatus === 'verified' ? 'text-green-500' : verificationStatus === 'failed' ? 'text-red-500' : 'text-amber-500'}`} />
                      <span className={`text-sm ${verificationStatus === 'verified' ? 'text-green-500' : verificationStatus === 'failed' ? 'text-red-500' : 'text-amber-500'}`}>
                        {verificationStatus === 'verified' ? 'Verified on Algorand Testnet' : verificationStatus === 'failed' ? 'Verification failed' : 'Verification in progress'}
                      </span>
                      {statusData?.registry_app_id && (
                        <Button variant="ghost" size="sm" className="p-0 h-auto" asChild>
                          <a href={`https://testnet.explorer.perawallet.app/application/${statusData.registry_app_id}`} target="_blank" rel="noreferrer"><ExternalLink className="h-3 w-3" /></a>
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              )}

              {complianceScore !== null && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <Button onClick={downloadOSCALReports} className="w-full" variant="outline" disabled={!artifactHash}>
                      <Download className="h-4 w-4 mr-2" />
                      Download OSCAL Reports
                    </Button>
                    <Button onClick={exportPdf} className="w-full" variant="secondary" disabled={!oscalLinks && (!findings || findings.length === 0) && complianceScore === null}>
                      Export to PDF
                    </Button>
                  </div>
                  {oscalLinks ? (
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {oscalLinks.component_definition && (<a className="underline" href={oscalLinks.component_definition} target="_blank" rel="noreferrer">• Component Definition</a>)}
                      {oscalLinks.assessment_plan && (<a className="underline" href={oscalLinks.assessment_plan} target="_blank" rel="noreferrer">• Assessment Plan</a>)}
                      {oscalLinks.assessment_results && (<a className="underline" href={oscalLinks.assessment_results} target="_blank" rel="noreferrer">• Assessment Results</a>)}
                      {oscalLinks.poam && (<a className="underline" href={oscalLinks.poam} target="_blank" rel="noreferrer">• POA&M</a>)}
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                      <span>• Component Definition</span>
                      <span>• Assessment Plan</span>
                      <span>• Assessment Results</span>
                      <span>• POA&M</span>
                    </div>
                  )}
                </div>
              )}

              {/* Findings Panel */}
              {findings && findings.length > 0 && (
                <div className="space-y-3">
                  <div className="text-sm font-semibold">Findings</div>
                  <div className="space-y-2 max-h-64 overflow-auto pr-1">
                    {findings.map((f, idx) => (
                      <div key={idx} className="p-3 border border-border rounded-md">
                        <div className="flex items-center justify-between gap-2">
                          <div className="text-sm font-medium truncate">{f.title || f.id || 'Finding'}</div>
                          {f.severity && (
                            <Badge variant={String(f.severity).toLowerCase() === 'high' ? 'destructive' : 'secondary'}>
                              {String(f.severity)}
                            </Badge>
                          )}
                        </div>
                        {f.description && (
                          <div className="mt-1 text-xs text-muted-foreground line-clamp-3">{f.description}</div>
                        )}
                        {Array.isArray(f.control_tags) && f.control_tags.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {f.control_tags.slice(0, 4).map((t: string, i: number) => (
                              <Badge key={i} variant="outline" className="text-[10px]">{t}</Badge>
                            ))}
                            {f.control_tags.length > 4 && (
                              <span className="text-[10px] text-muted-foreground">+{f.control_tags.length - 4} more</span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  {oscalLinks && (
                    <div className="text-xs text-muted-foreground">
                      Source: <a href={oscalLinks.assessment_results || oscalLinks.directory_url} target="_blank" rel="noreferrer" className="underline">assessment-results</a>
                    </div>
                  )}
                </div>
              )}

              {/* On-chain and IPFS links */}
              {artifactHash && statusData?.registry_app_id && (
                <div className="pt-4">
                  <OnChainLinks
                    registryAppId={statusData.registry_app_id}
                    registryTxId={statusData.registry_tx_id || null}
                    oracleTxId={statusData.oracle_tx_id || null}
                    artifactHash={artifactHash}
                    oscalCid={oscalLinks?.directory_cid || null}
                  />
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Features Overview */}
        <div className="grid md:grid-cols-3 gap-6 mt-12">
          <Card className="cosmic-glass text-center">
            <CardContent className="pt-6">
              <Shield className="h-8 w-8 mx-auto mb-3 text-primary" />
              <h3 className="font-semibold mb-2">AI-Powered Analysis</h3>
              <p className="text-sm text-muted-foreground">
                Advanced security analysis with automated control mapping
              </p>
            </CardContent>
          </Card>
          
          <Card className="cosmic-glass text-center">
            <CardContent className="pt-6">
              <FileCheck className="h-8 w-8 mx-auto mb-3 text-primary" />
              <h3 className="font-semibold mb-2">OSCAL Compliance</h3>
              <p className="text-sm text-muted-foreground">
                Official NIST schema validation and standardized reporting
              </p>
            </CardContent>
          </Card>
          
          <Card className="cosmic-glass text-center">
            <CardContent className="pt-6">
              <ExternalLink className="h-8 w-8 mx-auto mb-3 text-primary" />
              <h3 className="font-semibold mb-2">Blockchain Verified</h3>
              <p className="text-sm text-muted-foreground">
                Immutable proof anchored on Algorand blockchain
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default CompanyPortal;