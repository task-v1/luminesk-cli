import React, { useLayoutEffect, useRef } from 'react';
import gsap from 'gsap';

import HeartIcon from './heart.svg';
import styles from './Marquee.module.css';

interface Engine {
  name: string;
  url: string;
}

const ENGINES: Engine[] = [
  { name: "Nukkit", url: "https://github.com/cloudburstmc/nukkit" },
  { name: "PowerNukkitX", url: "https://github.com/PowerNukkitX/PowerNukkitX" },
  { name: "Nukkit-MOT", url: "https://github.com/MemoriesOfTime/Nukkit-MOT" },
  { name: "Lumi", url: "https://github.com/koshakminedev/lumi" },
  { name: "Allay", url: "https://github.com/AllayMC/Allay" },
  { name: "PocketMine-MP", url: "https://github.com/pmmp/pocketmine-mp" },
  { name: "BetterAltay", url: "https://github.com/Benedikt05/BetterAltay" },
  { name: "Lunacy", url: "https://github.com/karepanov35/Lunacy" },
  { name: "Dragonfly", url: "https://github.com/df-mc/dragonfly" },
  { name: "Pumpkin", url: "https://github.com/pumpkin-mc/pumpkin" },
  { name: "Serenity", url: "https://github.com/SerenityJS/serenity" },
  { name: "Endstone", url: "https://github.com/EndstoneMC/endstone" }

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

  const renderEngine = (engine: Engine, track: number, index: number) => (
    <a
      key={`${track}-${index}`}
      href={engine.url}
      target="_blank"
      rel="noopener noreferrer"
      className={styles.engineName}
    >
      {engine.name}
      {engine.name === 'Lumi' && (
        <HeartIcon className={styles.heartIcon} width="1em" height="1em" />
      )}
    </a>
  );

  return (
    <section className={`gsap-fade-up ${styles.marqueeSection}`}>
      <div className={styles.marqueeHeader}>Supported Engines</div>

      <div ref={marqueeRef} className={styles.marqueeContainer}>
        <div className={styles.marqueeTrack}>
          {ENGINES.map((engine, i) => renderEngine(engine, 1, i))}
        </div>
        <div className={styles.marqueeTrack} aria-hidden="true">
          {ENGINES.map((engine, i) => renderEngine(engine, 2, i))}
        </div>
        <div className={styles.marqueeTrack} aria-hidden="true">
          {ENGINES.map((engine, i) => renderEngine(engine, 3, i))}
        </div>
      </div>
    </section>
  );
}
