import { useEffect, useRef, type RefObject } from 'react';

/** Enhance visible content only; static HTML never depends on animation setup. */
export default function useLandingMotion(
  root: RefObject<HTMLElement | null>,
  paused: boolean,
): void {
  const entrances = useRef(new Set<Animation>());

  useEffect(() => {
    const element = root.current;
    if (!element) return;
    element.dataset.motionPaused = String(paused);
    if (paused) {
      entrances.current.forEach((animation) => animation.cancel());
      entrances.current.clear();
    }
  }, [paused, root]);

  useEffect(() => {
    const element = root.current;
    if (!element || !('IntersectionObserver' in window)) return;
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const seen = new WeakSet<Element>();
    let observer: IntersectionObserver | undefined;
    const activeEntrances = entrances.current;

    const cancelEntrances = () => {
      activeEntrances.forEach((animation) => animation.cancel());
      activeEntrances.clear();
    };
    const visibility = () => {
      element.dataset.pageHidden = String(document.hidden);
      if (document.hidden) cancelEntrances();
    };
    const configure = () => {
      observer?.disconnect();
      cancelEntrances();
      if (preference.matches) {
        delete element.dataset.motionReady;
        return;
      }
      element.dataset.motionReady = 'true';
      observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            const target = entry.target as HTMLElement;
            target.dataset.inView = String(entry.isIntersecting);
            if (!entry.isIntersecting || seen.has(target)) continue;
            seen.add(target);
            if (element.dataset.motionPaused === 'true' || document.hidden)
              continue;
            target
              .querySelectorAll<HTMLElement>('[data-reveal]')
              .forEach((child, index) => {
                const animation = child.animate(
                  [
                    { transform: 'translateY(36px)' },
                    { transform: 'translateY(0)' },
                  ],
                  {
                    duration: 900,
                    delay: index * 75,
                    easing: 'cubic-bezier(.16,1,.3,1)',
                  },
                );
                activeEntrances.add(animation);
                animation.onfinish = () => activeEntrances.delete(animation);
              });
          }
        },
        { threshold: 0.12 },
      );
      element
        .querySelectorAll('[data-motion-scene]')
        .forEach((scene) => observer?.observe(scene));
    };
    configure();
    visibility();
    preference.addEventListener('change', configure);
    document.addEventListener('visibilitychange', visibility);
    return () => {
      observer?.disconnect();
      cancelEntrances();
      preference.removeEventListener('change', configure);
      document.removeEventListener('visibilitychange', visibility);
      delete element.dataset.motionReady;
      delete element.dataset.pageHidden;
    };
  }, [root]);
}
