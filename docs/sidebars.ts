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
      items: ['server-lifecycle', 'cores-and-upgrades', 'runtime-and-docker'],
    },
    {
      type: 'category',
      label: 'Configuration',
      items: ['configuration-and-language'],
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
