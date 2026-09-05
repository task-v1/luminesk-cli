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
      label: 'Recipes',
      items: [
        'creating-a-recipe',
        'manifest-reference',
        'sources',
        'templates-and-inputs',
        'ownership',
        'checks',
        'manifest-and-lockfile',
      ],
    },
    {
      type: 'category',
      label: 'Reproducibility',
      items: ['lockfile-and-packages'],
    },
    {
      type: 'category',
      label: 'Support',
      items: ['troubleshooting', 'faq', 'migrating-to-2.0'],
    },
    {
      type: 'category',
      label: 'Contributing',
      items: ['development-and-contributing'],
    },
  ],
};

export default sidebars;
