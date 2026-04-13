// @ts-check

const repoName = "scriptoria";
const orgName = "nikazzio";

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Scriptoria",
  tagline: "A research workbench for IIIF manuscripts.",
  url: `https://${orgName}.github.io`,
  baseUrl: `/${repoName}/`,
  favicon: "img/scriptoria-header.svg",
  organizationName: orgName,
  projectName: repoName,
  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "throw",
  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },
  markdown: {
    mermaid: true,
  },
  themes: ["@docusaurus/theme-mermaid"],
  presets: [
    [
      "classic",
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          routeBasePath: "/",
          sidebarPath: require.resolve("./sidebars.js"),
          editUrl: `https://github.com/${orgName}/${repoName}/tree/main/`,
          exclude: ["wiki/**"],
        },
        blog: false,
        theme: {
          customCss: require.resolve("./src/css/custom.css"),
        },
      }),
    ],
  ],
  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      announcementBar: {
        id: "project-status",
        isCloseable: true,
        content:
          '<a href="https://github.com/nikazzio/scriptoria" target="_blank" rel="noopener noreferrer">GitHub</a> · ' +
          '<a href="https://github.com/nikazzio/scriptoria/issues" target="_blank" rel="noopener noreferrer">Issues</a> · ' +
          '<a href="https://github.com/nikazzio/scriptoria/releases" target="_blank" rel="noopener noreferrer">Releases</a> · ' +
          '<img alt="GitHub stars" src="https://img.shields.io/github/stars/nikazzio/scriptoria?style=flat-square&label=stars" /> ' +
          '<img alt="Open issues" src="https://img.shields.io/github/issues/nikazzio/scriptoria?style=flat-square&label=issues" />',
      },
      navbar: {
        title: "Scriptoria",
        logo: {
          alt: "Scriptoria",
          src: "img/scriptoria-header.svg",
          href: "/",
        },
        items: [
          {to: "/", label: "Docs", position: "left"},
          {to: "/reference/provider-support", label: "Libraries", position: "left"},
          {to: "/reference/configuration", label: "Configuration", position: "left"},
          {href: `https://github.com/${orgName}/${repoName}`, label: "GitHub", position: "right"},
          {href: `https://github.com/${orgName}/${repoName}/issues`, label: "Issues", position: "right"},
          {href: `https://github.com/${orgName}/${repoName}/wiki`, label: "Wiki", position: "right"},
        ],
      },
      footer: {
        style: "dark",
        links: [
          {
            title: "Docs",
            items: [
              {label: "Overview", to: "/"},
              {label: "Getting Started", to: "/intro/getting-started"},
              {label: "CLI Reference", to: "/reference/cli"},
            ],
          },
          {
            title: "Project",
            items: [
              {label: "GitHub", href: `https://github.com/${orgName}/${repoName}`},
              {label: "Issues", href: `https://github.com/${orgName}/${repoName}/issues`},
              {label: "Wiki", href: `https://github.com/${orgName}/${repoName}/wiki`},
            ],
          },
        ],
      },
      docs: {
        sidebar: {
          hideable: true,
        },
      },
      prism: {
        additionalLanguages: ["bash", "json"],
      },
    }),
};

module.exports = config;
