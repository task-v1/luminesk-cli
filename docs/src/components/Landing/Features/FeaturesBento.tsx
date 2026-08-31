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
    title: 'Docker Native Environments',
    desc: 'Every server runs inside isolated, secure, and resource-controlled Docker containers. Manage background execution, memory limits, and custom Java runtimes seamlessly.',
  },
  {
    spanClass: '',
    icon: <DiagnosticsIcon />,
    title: 'Smart Diagnostics',
    desc: 'Instantly evaluate your local environment, providers, and network settings.',
  },
  {
    spanClass: '',
    icon: <LoopIcon />,
    title: 'Loop Mode',
    desc: 'Keep your servers highly available. If a crash occurs, Luminesk-CLI automatically restarts the engine.',
  },
  {
    spanClass: styles.span2,
    icon: <MultiEngineIcon />,
    title: 'Multi-Engine Control',
    desc: 'Manage and switch between Nukkit, PowerNukkitX, Nukkit-MOT, and Lumi with just one command. Seamless updates and installations built right into the CLI.',
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
            Luminesk-CLI abstracts away the complexity of managing MCBE servers so you can focus on building your plugins and communities.
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
