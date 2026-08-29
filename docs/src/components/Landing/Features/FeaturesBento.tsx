import React, { useRef, useLayoutEffect } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import styles from './Features.module.css';
import landingStyles from '../Landing.module.css';

import DockerIcon from '../../../assets/icons/docker.svg';
import DiagnosticsIcon from './diagnostics.svg';
import LoopIcon from '../../../assets/icons/loop.svg';
import MultiEngineIcon from './multi-engine.svg';

gsap.registerPlugin(ScrollTrigger);

const featuresData = [
  {
    spanClass: styles.span2,
    icon: <DockerIcon />,
    title: 'Locked Docker Environments',
    desc: 'Runtime and build images are resolved to immutable repository digests, with explicit mounts, ports, limits, users, and readiness checks.',
  },
  {
    spanClass: '',
    icon: <DiagnosticsIcon />,
    title: 'Verified Inputs',
    desc: 'Bounded downloads, SHA-256 verification, safe archive extraction, and deterministic packages protect every installation boundary.',
  },
  {
    spanClass: '',
    icon: <LoopIcon />,
    title: 'Transactional Updates',
    desc: 'Preview ownership-aware changes, preserve user data, and restore the previous instance when validation or readiness fails.',
  },
  {
    spanClass: styles.span2,
    icon: <MultiEngineIcon />,
    title: 'Declarative Recipes',
    desc: 'Compose Nukkit, PowerNukkitX, Nukkit-MOT, Lumi, and other engines through one strict manifest, lockfile, and automation-friendly CLI.',
  }
];

const FeatureCard = ({ feature }: { feature: typeof featuresData[0] }) => {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    cardRef.current.style.setProperty('--mouse-x', `${x}px`);
    cardRef.current.style.setProperty('--mouse-y', `${y}px`);
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      className={`${landingStyles.glassPanel} ${styles.bentoCard} ${feature.spanClass}`}
    >
      <div className={styles.cardHoverGlow} />
      <div className={styles.cardIcon}>{feature.icon}</div>
      <div className={styles.cardContent}>
        <h3>{feature.title}</h3>
        <p>{feature.desc}</p>
      </div>
    </div>
  );
};

export default function FeaturesBento() {
  const gridRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const cards = gsap.utils.toArray<HTMLElement>(`.${styles.bentoCard}`);

      gsap.fromTo(cards,
        { opacity: 0, y: 50 },
        {
          scrollTrigger: {
            trigger: gridRef.current,
            start: "top 80%",
          },
          opacity: 1,
          y: 0,
          stagger: 0.1,
          duration: 0.8,
          ease: "power3.out"
        }
      );
    }, gridRef);
    return () => ctx.revert();
  }, []);

  return (
    <section className={styles.featuresSection}>
      <div className={landingStyles.container}>
        <div className="gsap-fade-up">
          <h2 style={{ fontSize: 'clamp(2rem, 4vw, 3rem)', fontWeight: 800, marginBottom: '1rem' }}>
            Infrastructure in <span className={landingStyles.gradientText}>One Tool.</span>
          </h2>
          <p style={{ color: 'var(--ifm-color-secondary)', maxWidth: '50ch', fontSize: '1.25rem' }}>
            Nesk makes source resolution, package ownership, Docker runtime, and rollback explicit and reviewable.
          </p>
        </div>

        <div ref={gridRef} className={styles.bentoGrid}>
          {featuresData.map((feature, idx) => (
            <FeatureCard key={idx} feature={feature} />
          ))}
        </div>
      </div>
    </section>
  );
}
