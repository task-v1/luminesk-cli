import React, { type ReactNode, useRef } from 'react';
import Link from '@docusaurus/Link';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { Compass } from '@phosphor-icons/react';
import type { Props } from '@theme/NotFound/Content';
import styles from './styles.module.css';

const LOG_DATA = [
  '[Luminesk] Daemon v1.2.0 starting...',
  '[Luminesk] Loading configuration: /etc/Luminesk/daemon.json',
  '[Luminesk] MCBE Server bridge listening on 0.0.0.0:19132',
  '[Luminesk] Connection established with Nukkit runtime',
  '[Luminesk] INFO: Thread pool size dynamically calibrated to 16 threads',
  '[Luminesk] WARNING: High packet latency detected on route PEER_0',
  '[Luminesk] CRITICAL: NullPointerException in com.Luminesk.bridge.RouteManager.route()',
  '[Luminesk] DEBUG: Stacktrace dump:',
  '    at com.Luminesk.bridge.RouteManager.route(RouteManager.java:84)',
  '    at com.Luminesk.bridge.Bridge.handlePacket(Bridge.java:192)',
  '    at java.base/java.lang.Thread.run(Thread.java:829)',
  '[Luminesk] SYSTEM: Attempting automatic hot-reload...',
  '[Luminesk] ERROR: ROUTE_NOT_FOUND (404)',
  '[Luminesk] SYSTEM: Memory state: 852MB / 2048MB',
  '[Luminesk] WARNING: Nosferatu protocol activated due to route failure',
  '[Luminesk] DEBUG: Pinging server at 127.0.0.1:19132 ... TIMEOUT',
  '[Luminesk] ERROR: Target server is unresponsive',
  '[Luminesk] INFO: Flushing routing table...',
  '[Luminesk] FATAL: Server crashed. Exit code 404',
  '[Luminesk] SYSTEM: Guided by Luminesk. Lost in the dark.'
];

const generateLogs = (count = 15) => {
  let logs: string[] = [];
  for (let i = 0; i < count; i++) {
    logs = logs.concat(LOG_DATA);
  }
  return logs.join('\n');
};

export default function NotFoundContent({ className }: Props): ReactNode {
  const containerRef = useRef<HTMLDivElement>(null);
  const spotlightRef = useRef<HTMLDivElement>(null);
  const nosferatuRef = useRef<HTMLParagraphElement>(null);
  const buttonRef = useRef<HTMLAnchorElement>(null);

  const logsText = React.useMemo(() => generateLogs(25), []);

  useGSAP(() => {
    if (!spotlightRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const spotlight = spotlightRef.current;

    gsap.set(spotlight, { xPercent: -50, yPercent: -50 });

    const xTo = gsap.quickTo(spotlight, 'left', { duration: 0.6, ease: 'power3.out' });
    const yTo = gsap.quickTo(spotlight, 'top', { duration: 0.6, ease: 'power3.out' });

    const idleTimeline = gsap.timeline({ repeat: -1 });

    idleTimeline.to(spotlight, {
      left: '30%',
      top: '25%',
      duration: 4,
      ease: 'sine.inOut',
    })
      .to(spotlight, {
        left: '70%',
        top: '65%',
        duration: 5,
        ease: 'sine.inOut',
      })
      .to(spotlight, {
        left: '20%',
        top: '60%',
        duration: 4,
        ease: 'sine.inOut',
      })
      .to(spotlight, {
        left: '50%',
        top: '40%',
        duration: 5,
        ease: 'sine.inOut',
      });

    const handleMouseMove = (e: MouseEvent) => {
      idleTimeline.pause();
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      xTo(x);
      yTo(y);
    };

    const handleMouseLeave = () => {
      idleTimeline.play();
    };

    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseleave', handleMouseLeave);

    gsap.to(nosferatuRef.current, {
      opacity: 0.7,
      duration: 2,
      delay: 10,
      ease: 'power2.inOut',
    });

    return () => {
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseleave', handleMouseLeave);
      idleTimeline.kill();
    };
  }, { scope: containerRef });

  useGSAP(() => {
    if (!buttonRef.current) return;
    const button = buttonRef.current;

    const onMouseMove = (e: MouseEvent) => {
      const rect = button.getBoundingClientRect();
      const x = e.clientX - (rect.left + rect.width / 2);
      const y = e.clientY - (rect.top + rect.height / 2);

      gsap.to(button, {
        x: x * 0.35,
        y: y * 0.35,
        duration: 0.3,
        ease: 'power2.out',
      });
    };

    const onMouseLeave = () => {
      gsap.to(button, {
        x: 0,
        y: 0,
        duration: 0.5,
        ease: 'elastic.out(1, 0.3)',
      });
    };

    button.addEventListener('mousemove', onMouseMove);
    button.addEventListener('mouseleave', onMouseLeave);

    return () => {
      button.removeEventListener('mousemove', onMouseMove);
      button.removeEventListener('mouseleave', onMouseLeave);
    };
  }, { scope: containerRef });

  return (
    <div className={styles.container} ref={containerRef}>
      <div className={styles.logsContainer}>
        {logsText}
      </div>

      <div className={styles.spotlight} ref={spotlightRef} />

      <div className={styles.card}>
        <h1 className={styles.glitchTitle}>404</h1>

        <p className={styles.easterEgg1}>
          Lost?
        </p>

        <p className={styles.easterEgg2} ref={nosferatuRef}>
          There is nothing here... Please come down from the moon to the earth.
        </p>

        <div className={styles.buttonContainer}>
          <Link
            to="/"
            className={styles.homeButton}
            ref={buttonRef}
          >
            <Compass weight="bold" size={18} />
            Go back down
          </Link>
        </div>
      </div>
    </div>
  );
}

