import React, { useState, useEffect } from 'react';
import Link from '@docusaurus/Link';

import CheckIcon from './check.svg';
import CopyIcon from './copy.svg';
import ArrowRightIcon from './arrow-right.svg';

import styles from './CTA.module.css';
import landingStyles from '../Landing.module.css';

type OS = 'Windows' | 'Linux' | 'macOS' | 'Unknown' | 'Loading';

export default function CTA() {
  const [os, setOs] = useState<OS>('Loading');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const ua = window.navigator.userAgent;
    if (/Windows/i.test(ua)) {
      setOs('Windows');
    } else if (/Macintosh|Mac OS X/i.test(ua)) {
      setOs('macOS');
    } else if (/Linux/i.test(ua) && !/Android/i.test(ua)) {
      setOs('Linux');
    } else {
      setOs('Unknown');
    }
  }, []);

  if (os === 'Loading' || os === 'Unknown') {
    return null;
  }

  const installCmd = os === 'Windows'
    ? "iwr -useb https://luminesk.taskov1ch.xyz/ps1 | iex"
    : "curl -fsSL https://luminesk.taskov1ch.xyz/sh | sh";

  const handleCopy = () => {
    navigator.clipboard.writeText(installCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className={`gsap-fade-up ${styles.ctaSection}`}>
      <div className={styles.ctaGlow} />

      <div className={`${landingStyles.container} ${styles.ctaContent}`}>
        <h2 className={styles.ctaTitle}>
          Ready to deploy?
        </h2>

        <div className={styles.terminalBox}>
          <span style={{ color: 'var(--ifm-color-primary)' }}>$</span>
          <span>{installCmd}</span>
          <button
            className={styles.copyButton}
            onClick={handleCopy}
            title="Copy to clipboard"
          >
            {copied ? (
              <CheckIcon width="20" height="20" />
            ) : (
              <CopyIcon width="20" height="20" />
            )}
          </button>
        </div>

        <Link to="/docs/installation/one-line-installer" className={styles.documentationLink}>
          Is your device not {os}?
          <ArrowRightIcon width="16" height="16" />
        </Link>
      </div>
    </section>
  );
}
