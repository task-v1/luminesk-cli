import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'intro',
    'getting-started',
    'installation',
    'quick-start',
    {
      type: 'category',
      label: 'Reference',
      items: ['command-reference'],
    },
    {
      type: 'category',
      label: 'Operations',
      items: ['recipes-and-updates', 'server-lifecycle', 'runtime-and-docker'],
    },
    {
      type: 'category',
      label: 'Contracts',
      items: ['manifest-and-lockfile'],
    },
    {
      type: 'category',
      label: 'Support',
      items: ['troubleshooting', 'faq'],
    },
    {
      type: 'category',
      label: 'Contributing',
      items: ['development-and-contributing'],
    },
  ],
};

export default sidebars;
