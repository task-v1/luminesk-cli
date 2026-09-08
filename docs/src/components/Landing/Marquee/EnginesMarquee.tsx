import React, { useLayoutEffect, useRef } from 'react';
import Link from '@docusaurus/Link';
import gsap from 'gsap';

import styles from './Marquee.module.css';

interface SourceProvider {
  name: string;
  url: string;
}

const SOURCE_PROVIDERS: SourceProvider[] = [
  { name: 'Direct HTTP', url: '/docs/sources#http' },
  { name: 'Maven', url: '/docs/sources#maven' },
  { name: 'Jenkins', url: '/docs/sources#jenkins' },
  { name: 'GitHub Releases', url: '/docs/sources#github-release' },
  { name: 'GitHub Source', url: '/docs/sources#github-source' },
  { name: 'GitLab Releases', url: '/docs/sources#gitlab-release' },
  { name: 'GitLab Job Artifacts', url: '/docs/sources#gitlab-job-artifact' },
  { name: 'Mojang Versions', url: '/docs/sources#mojang-version' },
  { name: 'Paper Downloads', url: '/docs/sources#paper' },
  { name: 'Local Files', url: '/docs/sources#local-file' },
];

export default function EnginesMarquee() {
  const marqueeRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const container = marqueeRef.current;
      if (!container) return;

      const track1 = container.children[0] as HTMLElement;
      const trackWidth = track1.offsetWidth;

      gsap.to(container, {
        x: -trackWidth,
        ease: "none",
        duration: 40,
        repeat: -1
      });
    }, marqueeRef);

    return () => ctx.revert();
  }, []);

  const renderProvider = (provider: SourceProvider, track: number, index: number) => (
    <Link
      key={`${track}-${index}`}
      to={provider.url}
      className={styles.engineName}
    >
      {provider.name}
    </Link>
  );

  return (
    <section className={`gsap-fade-up ${styles.marqueeSection}`}>
      <div className={styles.marqueeHeader}>Source Providers</div>

      <div ref={marqueeRef} className={styles.marqueeContainer}>
        <div className={styles.marqueeTrack}>
          {SOURCE_PROVIDERS.map((provider, i) => renderProvider(provider, 1, i))}
        </div>
        <div className={styles.marqueeTrack} aria-hidden="true">
          {SOURCE_PROVIDERS.map((provider, i) => renderProvider(provider, 2, i))}
        </div>
        <div className={styles.marqueeTrack} aria-hidden="true">
          {SOURCE_PROVIDERS.map((provider, i) => renderProvider(provider, 3, i))}
        </div>
      </div>
    </section>
  );
}
