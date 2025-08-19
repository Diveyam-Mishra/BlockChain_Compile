import React from 'react';
import { Shield, Users, FileCheck, ExternalLink, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Link } from 'react-router-dom';

const CompliPortalHome = () => {
  return (
    <div className="min-h-screen bg-background cosmic-grid">
      {/* Header */}
      <header className="border-b border-border backdrop-blur-sm bg-background/80 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">CompliLedger</h1>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            <Link to="/company" className="text-sm hover:text-primary transition-colors">
              Company Portal
            </Link>
            <Link to="/auditor" className="text-sm hover:text-primary transition-colors">
              Auditor Portal
            </Link>
            <Button variant="outline" size="sm">
              Documentation
            </Button>
          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-12 space-y-16">
        {/* Hero Section */}
        <section className="text-center space-y-8">
          <div className="space-y-4">
            <h1 className="text-5xl font-bold tracking-tighter text-foreground">
              AI-Powered Compliance
              <br />
              <span className="text-primary">Verification Platform</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              OSCAL-integrated hybrid on-chain AI SBOM verification with independent auditor portal. 
              Blockchain-anchored compliance evidence with NIST-standardized reporting.
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="text-lg px-8">
              <Link to="/company">
                Company Portal
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="text-lg px-8">
              <Link to="/auditor">
                Auditor Portal
                <Users className="ml-2 h-5 w-5" />
              </Link>
            </Button>
          </div>
        </section>

        {/* Features Grid */}
        <section className="space-y-8">
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold tracking-tight">
              Standards-First Compliance
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Built on OSCAL standards with blockchain verification and AI-enhanced analysis
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card className="cosmic-glass">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileCheck className="h-5 w-5 text-blue-500" />
                  OSCAL Integration
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Official NIST OSCAL compliance with automated Component Definition, 
                  Assessment Plan, Results, and POA&M generation.
                </p>
              </CardContent>
            </Card>

            <Card className="cosmic-glass">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-green-500" />
                  Blockchain Anchored
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Immutable verification evidence anchored on Algorand blockchain 
                  with IPFS document storage for tamper-proof compliance records.
                </p>
              </CardContent>
            </Card>

            <Card className="cosmic-glass">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-purple-500" />
                  Dual Portal Architecture
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Separate company and auditor interfaces enabling independent 
                  verification while protecting sensitive intellectual property.
                </p>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* User Flows */}
        <section className="space-y-8">
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold tracking-tight">
              Streamlined Compliance Flows
            </h2>
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            {/* Company Flow */}
            <Card className="cosmic-glass">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileCheck className="h-5 w-5" />
                  Company Flow
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">1</div>
                    <span className="text-sm">Upload SBOM/Smart Contract</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">2</div>
                    <span className="text-sm">Select Compliance Standard</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">3</div>
                    <span className="text-sm">AI Analysis & Control Mapping</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">4</div>
                    <span className="text-sm">Blockchain Verification</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">5</div>
                    <span className="text-sm">Download OSCAL Reports</span>
                  </div>
                </div>
                <Button asChild className="w-full">
                  <Link to="/company">Start Company Portal</Link>
                </Button>
              </CardContent>
            </Card>

            {/* Auditor Flow */}
            <Card className="cosmic-glass">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Auditor Flow
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-secondary text-secondary-foreground text-xs flex items-center justify-center">1</div>
                    <span className="text-sm">Search Controls/Artifacts</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-secondary text-secondary-foreground text-xs flex items-center justify-center">2</div>
                    <span className="text-sm">View Compliance Claims</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-secondary text-secondary-foreground text-xs flex items-center justify-center">3</div>
                    <span className="text-sm">Verify on Blockchain</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-secondary text-secondary-foreground text-xs flex items-center justify-center">4</div>
                    <span className="text-sm">Download OSCAL Documents</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-secondary text-secondary-foreground text-xs flex items-center justify-center">5</div>
                    <span className="text-sm">Export Audit Trail</span>
                  </div>
                </div>
                <Button asChild variant="outline" className="w-full">
                  <Link to="/auditor">Access Auditor Portal</Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Technical Stack */}
        <section className="space-y-8">
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold tracking-tight">
              Enterprise-Grade Architecture
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="cosmic-glass text-center">
              <CardContent className="pt-6">
                <div className="w-12 h-12 bg-primary/10 rounded-lg mx-auto mb-3 flex items-center justify-center">
                  <Shield className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-semibold mb-2">NIST OSCAL</h3>
                <p className="text-sm text-muted-foreground">
                  Standards-compliant documentation and control mapping
                </p>
              </CardContent>
            </Card>

            <Card className="cosmic-glass text-center">
              <CardContent className="pt-6">
                <div className="w-12 h-12 bg-blue-500/10 rounded-lg mx-auto mb-3 flex items-center justify-center">
                  <ExternalLink className="h-6 w-6 text-blue-500" />
                </div>
                <h3 className="font-semibold mb-2">Algorand</h3>
                <p className="text-sm text-muted-foreground">
                  Blockchain anchoring for immutable verification proof
                </p>
              </CardContent>
            </Card>

            <Card className="cosmic-glass text-center">
              <CardContent className="pt-6">
                <div className="w-12 h-12 bg-green-500/10 rounded-lg mx-auto mb-3 flex items-center justify-center">
                  <FileCheck className="h-6 w-6 text-green-500" />
                </div>
                <h3 className="font-semibold mb-2">IPFS Storage</h3>
                <p className="text-sm text-muted-foreground">
                  Decentralized document storage with content addressing
                </p>
              </CardContent>
            </Card>

            <Card className="cosmic-glass text-center">
              <CardContent className="pt-6">
                <div className="w-12 h-12 bg-purple-500/10 rounded-lg mx-auto mb-3 flex items-center justify-center">
                  <Users className="h-6 w-6 text-purple-500" />
                </div>
                <h3 className="font-semibold mb-2">AI Analysis</h3>
                <p className="text-sm text-muted-foreground">
                  Automated security analysis and compliance verification
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-16">
        <div className="max-w-6xl mx-auto px-6 py-8 text-center text-muted-foreground">
          <p>CompliLedger - AI-Powered Compliance Verification Platform</p>
        </div>
      </footer>
    </div>
  );
};

export default CompliPortalHome;