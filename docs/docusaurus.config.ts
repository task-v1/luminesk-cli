import { themes as prismThemes } from 'prism-react-renderer';
import type { Config } from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Luminesk-CLI',
  tagline: 'CLI manager for MCBE servers',
  favicon: 'img/favicon.ico',
  headTags: [
  {
    tagName: "meta",
    attributes: {
      property: "og:site_name",
      content: "Luminesk-CLI",
    },
  },
  {
    tagName: "script",
    attributes: {
      type: "application/ld+json",
    },
    innerHTML: JSON.stringify({
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: "Luminesk-CLI",
      url: "https://luminesk.taskov1ch.xyz/",
    }),
  },
  ],



  url: 'https://luminesk.taskov1ch.xyz',
  baseUrl: '/',
  organizationName: 'task-v1',
  projectName: 'luminesk-cli',

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
        },
        blog: false, // {
        //   showReadingTime: false,
        //   feedOptions: {
        //     type: ['rss', 'atom'],
        //     xslt: true,
        //   },
        //   onInlineTags: 'warn',
        //   onInlineAuthors: 'warn',
        //   onUntruncatedBlogPosts: 'warn',
        // },
        theme: {
          customCss: './src/css/custom.css',
        },
        sitemap: {
          changefreq: 'weekly',
          createSitemapItems: async (params) => {
            const { defaultCreateSitemapItems } = params;
            const items = await defaultCreateSitemapItems(params);
            
            return items.map((item) => {
              if (item.url === 'https://luminesk.taskov1ch.xyz' || item.url === 'https://luminesk.taskov1ch.xyz/') {
                return { ...item, priority: 1.0 };
              }
              
              if (item.url.includes('/docs/getting-started') || item.url.includes('/docs/installation')) {
                return { ...item, priority: 0.8 };
              }
              
              return item;
            });
          },
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/sc.png',
    colorMode: {
      respectPrefersColorScheme: false,
      defaultMode: 'dark',
      disableSwitch: true,
    },
    navbar: {
      logo: {
        alt: 'Luminesk-CLI',
        src: 'img/logo.svg',
        width: 110,
        height: 22,
      },
      items: [
        // { to: '/blog', label: 'Blog', position: 'left' },
        {
          href: 'https://github.com/task-v1/luminesk-cli',
          position: 'right',
          className: 'header-github-link navbar-sidebar__item--hidden',
          'aria-label': 'GitHub repository',
        },
      ],
    },
    footer: {
      style: 'dark',
      // links: [],
      copyright: `<span class='primary'>Luminesk-CLI</span> is released under the
                <a href="https://github.com/task-v1/luminesk-cli/blob/main/LICENSE" target="_blank" rel="noopener noreferrer">GNU GPLv3 License</a>.
                The gradient background in the Hero section is created using
                <a href="https://neat.firecms.co/" target="_blank" rel="noopener noreferrer">NEAT</a>.
                Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'powershell', 'json', 'python', 'yaml'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
