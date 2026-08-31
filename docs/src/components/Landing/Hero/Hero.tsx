import React, { useEffect, useRef } from 'react';
import Link from '@docusaurus/Link';
import gsap from 'gsap';
import HeroBackground from './HeroBackground';
import Logo from './Logo';
import ArrowRightIcon from './arrow-right.svg';

import styles from './Hero.module.css';
import landingStyles from '../Landing.module.css';

export default function Hero() {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const paths = document.querySelectorAll(`.${styles.logoPath}`);
      const circles = document.querySelectorAll(`.${styles.logoCircle}`);

      paths.forEach((path) => {
        const svgPath = path as SVGPathElement;
        const length = svgPath.getTotalLength();
        gsap.set(svgPath, {
          strokeDasharray: length,
          strokeDashoffset: length,
          opacity: 0
        });
      });

      gsap.set(circles, { opacity: 0 });
      gsap.set(overlayRef.current, { opacity: 1, display: 'flex' });
      gsap.set(`.${styles.heroContent}`, { zIndex: 10001 });
      gsap.set(`.${styles.revealContent}`, { opacity: 0, y: 30 });
      gsap.set(`.${styles.cliPillGroup}`, { opacity: 0, x: -30 });

      const tl = gsap.timeline({ delay: 0.3 });

      paths.forEach((path, index) => {
        const svgPath = path as SVGPathElement;

        if (index === 3) {
          tl.to(svgPath, {
            opacity: 1,
            strokeDashoffset: 0,
            duration: 0.4,
            ease: "power2.out"
          }, index * 0.08);

          tl.to(circles, {
            opacity: 1,
            duration: 0.2,
            ease: "power1.out"
          }, index * 0.08 + 0.2);
        } else {
          tl.to(svgPath, {
            opacity: 1,
            strokeDashoffset: 0,
            duration: 0.4,
            ease: "power2.out"
          }, index * 0.08);
        }
      });

      tl.to(`.${styles.cliPillGroup}`, {
        opacity: 1,
        x: 0,
        duration: 0.6,
        ease: "power2.out"
      }, 0.9);

      tl.to(overlayRef.current, {
        opacity: 0,
        duration: 0.8,
        ease: "power2.inOut",
        onComplete: () => {
          gsap.set(overlayRef.current, { display: 'none' });
          gsap.set(`.${styles.heroContent}`, { zIndex: 2 });
        }
      }, 0.5);

      tl.to(`.${styles.revealContent}`, {
        opacity: 1,
        y: 0,
        duration: 0.8,
        ease: "power3.out"
      }, 0.7);
    });

    return () => {
      ctx.revert();
    };
  }, []);

  return (
    <section className={styles.heroSection}>
      <div ref={overlayRef} className={styles.introOverlay} />

      <HeroBackground />
      <div className={styles.heroOverlayDarken} />
      <div className={styles.heroOverlayFadeBottom} />

      <div className={`${landingStyles.container} ${styles.heroContent}`}>
        <div className={styles.logoContainer}>
          <Logo />
        </div>

        <div className={styles.revealContent}>
          <p className={styles.heroSubtitle}>
            Deploy MCBE Servers with Zero Friction.
          </p>

          <div className={styles.buttonGroup}>
            <Link to="/docs" className={styles.primaryButton}>
              Get Started
              <ArrowRightIcon width="20" height="20" />
            </Link>
            <a href="https://github.com/task-v1/luminesk-cli" target="_blank" rel="noreferrer" className={styles.secondaryButton}>
              View Source
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
