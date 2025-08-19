
import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import Header from '@/components/Header';
import HeroSection from '@/components/HeroSection';
import Features from '@/components/Features';
import Testimonials from '@/components/Testimonials';
import Pricing from '@/components/Pricing';
import Footer from '@/components/Footer';

const Index = () => {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Header />
      <main>
        <HeroSection />
        
        {/* Product Overview Section (professional landing) */}
        <section className="py-20 bg-muted/30">
          <div className="max-w-6xl mx-auto px-6">
            <Card className="cosmic-glass overflow-hidden">
              <CardContent className="p-12">
                <div className="text-center space-y-4 mb-12">
                  <div className="flex items-center justify-center gap-3">
                    <Shield className="h-8 w-8 text-primary" />
                    <h2 className="text-3xl font-bold tracking-tight">CompliLedger Platform</h2>
                  </div>
                  <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
                    Enterprise-grade compliance automation that turns your SBOMs and smart contracts into OSCAL-native reports,
                    anchored on-chain for audit-ready, tamper-evident proof.
                  </p>
                </div>

                {/* Value pillars */}
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                  <Card className="cosmic-glass text-center">
                    <CardContent className="pt-6">
                      <h3 className="font-semibold mb-2">AI Compliance Verification</h3>
                      <p className="text-sm text-muted-foreground">Automated control mapping and risk findings in minutes.</p>
                    </CardContent>
                  </Card>
                  <Card className="cosmic-glass text-center">
                    <CardContent className="pt-6">
                      <h3 className="font-semibold mb-2">OSCAL-First Reporting</h3>
                      <p className="text-sm text-muted-foreground">Generate assessment results, plans, and POA&M in NIST OSCAL.</p>
                    </CardContent>
                  </Card>
                  <Card className="cosmic-glass text-center">
                    <CardContent className="pt-6">
                      <h3 className="font-semibold mb-2">Blockchain Anchoring</h3>
                      <p className="text-sm text-muted-foreground">Immutable verification on Algorand with IPFS-backed artifacts.</p>
                    </CardContent>
                  </Card>
                  <Card className="cosmic-glass text-center">
                    <CardContent className="pt-6">
                      <h3 className="font-semibold mb-2">Auditor Collaboration</h3>
                      <p className="text-sm text-muted-foreground">Independent attestations referencing the same anchored proof.</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Primary CTAs */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <Button asChild size="lg" className="text-lg px-8">
                    <Link to="/company">
                      Launch Company Portal
                      <ArrowRight className="ml-2 h-5 w-5" />
                    </Link>
                  </Button>
                  <Button asChild variant="outline" size="lg" className="text-lg px-8">
                    <Link to="/auditor">Explore Auditor Portal</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
        
        <Features />
        <Testimonials />
        <Pricing />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
