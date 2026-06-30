import React, { useLayoutEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Layout from '@theme/Layout';

import styles from './Landing.module.css';
import Hero from './Hero/Hero';
import FeaturesBento from './Features/FeaturesBento';
import EnginesMarquee from './Marquee/EnginesMarquee';
import CTA from './CTA/CTA';

gsap.registerPlugin(ScrollTrigger);

export default function Landing() {
  const containerRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (typeof window !== 'undefined') {
      const isLandingPath = window.location.pathname === '/' || window.location.pathname === '/index.html';
      const hasHash = !!window.location.hash;

      if (!isLandingPath || hasHash) {
        return;
      }

      const originalScrollRestoration = 'scrollRestoration' in window.history ? window.history.scrollRestoration : 'auto';
      if ('scrollRestoration' in window.history) {
        window.history.scrollRestoration = 'manual';
      }

      const html = document.documentElement;
      const originalScrollBehavior = html.style.scrollBehavior;
      html.style.scrollBehavior = 'auto';
      window.scrollTo(0, 0);
      html.style.scrollBehavior = originalScrollBehavior;

      const rafId = requestAnimationFrame(() => {
        const html = document.documentElement;
        const originalScrollBehavior = html.style.scrollBehavior;
        html.style.scrollBehavior = 'auto';
        window.scrollTo(0, 0);
        html.style.scrollBehavior = originalScrollBehavior;
      });

      return () => {
        cancelAnimationFrame(rafId);
        if ('scrollRestoration' in window.history) {
          window.history.scrollRestoration = originalScrollRestoration;
        }
      };
    }
  }, []);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>('.gsap-fade-up').forEach((el) => {
        gsap.fromTo(
          el,
          { opacity: 0, y: 40 },
          {
            scrollTrigger: {
              trigger: el,
              start: 'top 85%',
              toggleActions: 'play none none reverse',
            },
            opacity: 1,
            y: 0,
            duration: 0.8,
            ease: 'power3.out',
          }
        );
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <Layout
      title="Luminesk CLI - CLI manager for MCBE servers"
      description="CLI manager for MCBE servers. Manage your servers with ease and efficiency.">
      <main ref={containerRef} className={styles.landingWrapper}>
        <Hero />
        <FeaturesBento />
        <EnginesMarquee />
        <CTA />
      </main>
    </Layout>
  );
}
