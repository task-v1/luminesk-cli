import React, { type ReactNode } from 'react';
import styles from './Landing.module.css';

/** Vector light ribbons stay visible without JavaScript and need no render loop. */
export default function BrandAtmosphere(): ReactNode {
  return (
    <div className={styles.atmosphere} aria-hidden="true">
      <svg
        viewBox="0 0 1440 900"
        preserveAspectRatio="xMidYMid slice"
        focusable="false"
      >
        <defs>
          <linearGradient id="ribbonLight" x1="0" y1="1" x2="1" y2="0">
            <stop stopColor="#19000b" />
            <stop offset=".38" stopColor="#b90043" />
            <stop offset=".56" stopColor="#ff0058" />
            <stop offset=".69" stopColor="#ff80a9" />
            <stop offset=".77" stopColor="#630023" />
            <stop offset="1" stopColor="#050505" />
          </linearGradient>
          <linearGradient id="ribbonEdge" x1="0" y1="1" x2="1" y2="0">
            <stop stopColor="#ff0058" stopOpacity="0" />
            <stop offset=".5" stopColor="#ff80a9" stopOpacity=".8" />
            <stop offset="1" stopColor="#ff0058" stopOpacity="0" />
          </linearGradient>
        </defs>
        <g className={styles.ribbonBack}>
          <path
            d="M-240 650 C140 1110 660 570 930 460 S1470 180 1580 -130 L1630 230 C1340 620 1090 570 870 620 S220 1200 -240 850Z"
            fill="url(#ribbonLight)"
          />
          <path
            d="M-240 650 C140 1110 660 570 930 460 S1470 180 1580 -130"
            fill="none"
            stroke="url(#ribbonEdge)"
            strokeWidth="2"
          />
        </g>
        <g className={styles.ribbonFront}>
          <path
            d="M-260 -150 C100 160 30 360 280 500 S950 490 1700 890 L1650 1080 C1040 490 590 750 270 670 S30 280 -260 120Z"
            fill="url(#ribbonLight)"
          />
          <path
            d="M-260 -150 C100 160 30 360 280 500 S950 490 1700 890"
            fill="none"
            stroke="url(#ribbonEdge)"
            strokeWidth="2"
          />
        </g>
        <g
          className={styles.ribbonThread}
          fill="none"
          stroke="url(#ribbonEdge)"
        >
          <path d="M-100 420 C340 960 550 280 1600 510" />
          <path d="M-100 435 C340 975 550 295 1600 525" strokeOpacity=".4" />
          <path d="M-100 450 C340 990 550 310 1600 540" strokeOpacity=".2" />
        </g>
      </svg>
      <div className={styles.atmosphereVeil} />
    </div>
  );
}
