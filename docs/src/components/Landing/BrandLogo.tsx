import React, { useEffect, useRef, type ReactNode } from 'react';
import gsap from 'gsap';
import styles from './Landing.module.css';

export default function BrandLogo(): ReactNode {
  const root = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = root.current;
    const main = svg?.closest('main');
    const scene = svg?.closest<HTMLElement>('[data-motion-scene]');
    if (!svg || !main || !scene) return;

    let context: gsap.Context | undefined;
    let intro: gsap.core.Timeline | undefined;
    let gradient: gsap.core.Tween | undefined;
    const configure = () => {
      if (!main.hasAttribute('data-motion-ready')) {
        context?.revert();
        context = undefined;
        return;
      }
      if (!context) {
        context = gsap.context(() => {
          const paths = svg.querySelectorAll('path');
          const dot = svg.querySelector('circle');
          const pill = svg.querySelector('g');
          paths.forEach((path) => {
            const length = path.getTotalLength();
            gsap.set(path, {
              strokeDasharray: length,
              strokeDashoffset: length,
              opacity: 0,
            });
          });
          gsap.set(dot, { opacity: 0 });
          gsap.set(pill, { opacity: 0, x: -30 });

          // Preserve the logo timeline from v1.1.0's Hero.tsx.
          intro = gsap.timeline({ delay: 0.3 });
          paths.forEach((path, index) => {
            intro?.to(
              path,
              {
                opacity: 1,
                strokeDashoffset: 0,
                duration: 0.4,
                ease: 'power2.out',
              },
              index * 0.08,
            );
          });
          intro.to(
            dot,
            {
              opacity: 1,
              duration: 0.2,
              ease: 'power1.out',
            },
            3 * 0.08 + 0.2,
          );
          intro.to(
            pill,
            {
              opacity: 1,
              x: 0,
              duration: 0.6,
              ease: 'power2.out',
            },
            0.9,
          );

          // The original SVG moves both gradient endpoints linearly every 5s.
          gradient = gsap.fromTo(
            svg.querySelector('linearGradient'),
            {
              attr: { x1: '0%', x2: '200%' },
            },
            {
              attr: { x1: '-100%', x2: '100%' },
              duration: 5,
              repeat: -1,
              ease: 'none',
            },
          );
        }, svg);
      }
      const paused =
        main.dataset.motionPaused === 'true' ||
        main.dataset.pageHidden === 'true' ||
        scene.dataset.inView !== 'true';
      intro?.paused(paused);
      gradient?.paused(paused);
    };
    const observer = new MutationObserver(configure);
    observer.observe(main, {
      attributes: true,
      attributeFilter: [
        'data-motion-ready',
        'data-motion-paused',
        'data-page-hidden',
      ],
    });
    observer.observe(scene, {
      attributes: true,
      attributeFilter: ['data-in-view'],
    });
    configure();
    return () => {
      observer.disconnect();
      context?.revert();
    };
  }, []);

  return (
    <svg
      ref={root}
      viewBox="0 0 1200 200"
      className={styles.logoSvg}
      role="img"
      aria-label="Luminesk-CLI"
    >
      <defs>
        <linearGradient
          id="heroBrandGradient"
          gradientUnits="userSpaceOnUse"
          x1="0%"
          y1="0%"
          x2="200%"
          y2="0%"
        >
          <stop offset="0%" stopColor="#FF0058" />
          <stop offset="25%" stopColor="#FF80A9" />
          <stop offset="50%" stopColor="#FF0058" />
          <stop offset="75%" stopColor="#FF80A9" />
          <stop offset="100%" stopColor="#FF0058" />
        </linearGradient>
      </defs>
      {/* l */}
      <path
        d="M12.5 13V135C12.5 143.5 16.5 158.5 44 158.5"
        stroke="url(#heroBrandGradient)"
        strokeWidth="25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={styles.logoPath}
      />
      {/* u */}
      <path
        d="M83 63L83 107C83 136.5 97.4792 159.5 130 159.5C162.5 159.5 179 136 179 107V63"
        stroke="url(#heroBrandGradient)"
        strokeWidth="25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={styles.logoPath}
      />
      {/* m */}
      <path
        d="M230 160V100C230 83 239.472 62 265.5 62C291.5 62 304.5 81 304.5 100M304.5 100V160M304.5 100C304.5 81 317.1 62 341.5 62C365.9 62 378.5 78.5 378.5 100V160"
        stroke="url(#heroBrandGradient)"
        strokeWidth="25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={styles.logoPath}
      />
      {/* i stem */}
      <path
        d="M436 64V159"
        stroke="url(#heroBrandGradient)"
        strokeWidth="25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={styles.logoPath}
      />
      {/* n */}
      <path
        d="M489 160.5L489 116.5C489 87 503.479 64 536 64C568.5 64 585 87.5 585 116.5V160.5"
        stroke="white"
        strokeWidth="25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={styles.logoPath}
      />
      {/* e */}
      <path
        d="M720 159.5H680C657 159.5 634.5 144.421 634.5 110M634.5 110C634.5 47.5 728 46 728 110M634.5 110H724.5"
        stroke="white"
        strokeWidth="25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={styles.logoPath}
      />
      {/* s */}
      <path
        d="M775 159.5H823.5C841 159.5 851.943 150.494 851.5 135C851 117.5 840.5 112 819 112H797C789.667 112 775 105.9 775 87.5C775 69.1 789.5 63.5 806.5 63.5H849.5"
        stroke="white"
        strokeWidth="25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={styles.logoPath}
      />
      {/* k */}
      <path
        d="M901.5 12.5V125M901.5 159.5V125M901.5 125L923.5 106M973 61.5L923.5 106M923.5 106L973 159.5"
        stroke="white"
        strokeWidth="25"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={styles.logoPath}
      />
      {/* "i" dot */}
      <circle
        cx="436"
        cy="20"
        r="13"
        fill="url(#heroBrandGradient)"
        className={styles.logoDot}
      />

      {/* CLI Pill embedded inside SVG for unified scaling */}
      <g className={styles.cliPill}>
        <rect
          x="1013"
          y="55"
          width="160"
          height="90"
          rx="45"
          ry="45"
          fill="white"
        />
        <text
          x="1093"
          y="102"
          fill="black"
          textAnchor="middle"
          dominantBaseline="central"
          className={styles.cliText}
        >
          CLI
        </text>
      </g>
    </svg>
  );
}
