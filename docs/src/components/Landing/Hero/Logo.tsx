import React from 'react';
import styles from './Hero.module.css';

export default function Logo() {
  return (
    <svg viewBox="0 0 1200 200" className={styles.logoSvg}>
      <defs>
        <linearGradient id="lumiGradient" gradientUnits="userSpaceOnUse" x1="0%" y1="0%" x2="200%" y2="0%">
          <stop offset="0%" stopColor="#FF0058" />
          <stop offset="25%" stopColor="#FF80A9" />
          <stop offset="50%" stopColor="#FF0058" />
          <stop offset="75%" stopColor="#FF80A9" />
          <stop offset="100%" stopColor="#FF0058" />
          <animate attributeName="x1" values="0%; -100%" dur="5s" repeatCount="indefinite" />
          <animate attributeName="x2" values="200%; 100%" dur="5s" repeatCount="indefinite" />
        </linearGradient>
      </defs>
      {/* l */}
      <path d="M12.5 13V135C12.5 143.5 16.5 158.5 44 158.5" stroke="url(#lumiGradient)" strokeWidth="25" strokeLinecap="round" strokeLinejoin="round" className={styles.logoPath} />
      {/* u */}
      <path d="M83 63L83 107C83 136.5 97.4792 159.5 130 159.5C162.5 159.5 179 136 179 107V63" stroke="url(#lumiGradient)" strokeWidth="25" strokeLinecap="round" strokeLinejoin="round" className={styles.logoPath} />
      {/* m */}
      <path d="M230 160V100C230 83 239.472 62 265.5 62C291.5 62 304.5 81 304.5 100M304.5 100V160M304.5 100C304.5 81 317.1 62 341.5 62C365.9 62 378.5 78.5 378.5 100V160" stroke="url(#lumiGradient)" strokeWidth="25" strokeLinecap="round" strokeLinejoin="round" className={styles.logoPath} />
      {/* i stem */}
      <path d="M436 64V159" stroke="url(#lumiGradient)" strokeWidth="25" strokeLinecap="round" strokeLinejoin="round" className={styles.logoPath} />
      {/* n */}
      <path d="M489 160.5L489 116.5C489 87 503.479 64 536 64C568.5 64 585 87.5 585 116.5V160.5" stroke="white" strokeWidth="25" strokeLinecap="round" strokeLinejoin="round" className={styles.logoPath} />
      {/* e */}
      <path d="M720 159.5H680C657 159.5 634.5 144.421 634.5 110M634.5 110C634.5 47.5 728 46 728 110M634.5 110H724.5" stroke="white" strokeWidth="25" strokeLinecap="round" strokeLinejoin="round" className={styles.logoPath} />
      {/* s */}
      <path d="M775 159.5H823.5C841 159.5 851.943 150.494 851.5 135C851 117.5 840.5 112 819 112H797C789.667 112 775 105.9 775 87.5C775 69.1 789.5 63.5 806.5 63.5H849.5" stroke="white" strokeWidth="25" strokeLinecap="round" strokeLinejoin="round" className={styles.logoPath} />
      {/* k */}
      <path d="M901.5 12.5V125M901.5 159.5V125M901.5 125L923.5 106M973 61.5L923.5 106M923.5 106L973 159.5" stroke="white" strokeWidth="25" strokeLinecap="round" strokeLinejoin="round" className={styles.logoPath} />
      {/* "i" dot */}
      <circle cx="436" cy="20" r="13" fill="url(#lumiGradient)" className={styles.logoCircle} />

      {/* CLI Pill embedded inside SVG for unified scaling */}
      <g className={styles.cliPillGroup}>
        <rect x="1013" y="55" width="160" height="90" rx="45" ry="45" fill="white" />
        <text x="1093" y="102" fill="black" textAnchor="middle" dominantBaseline="central" className={styles.cliText}>CLI</text>
      </g>
    </svg>
  );
}
