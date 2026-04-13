// @ts-check

const repoName = "scriptoria";
const orgName = "nikazzio";

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "Scriptoria",
  tagline: "A research workbench for IIIF manuscripts.",
  url: `https://${orgName}.github.io`,
  baseUrl: `/${repoName}/`,
  organizationName: orgName,
  projectName: repoName,
  onBrokenLinks: "throw",
  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },
  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: "throw",
    },
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
      navbar: {
        title: "Scriptoria",
        items: [
          {to: "/", label: "Docs", position: "left"},
          {href: `https://github.com/${orgName}/${repoName}`, label: "GitHub", position: "right"},
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
