/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    "index",
    {
      type: "category",
      label: "Intro",
      items: ["intro/getting-started"],
    },
    {
      type: "category",
      label: "Guides",
      items: [
        "guides/first-manuscript-workflow",
        "guides/discovery-and-library",
        "guides/studio-workflow",
        "guides/pdf-export",
        "guides/troubleshooting",
      ],
    },
    {
      type: "category",
      label: "Reference",
      items: [
        "reference/configuration",
        "reference/cli",
        "reference/runtime-paths",
        "reference/provider-support",
        "CONFIG_REFERENCE",
      ],
    },
    {
      type: "category",
      label: "Explanation",
      items: [
        "explanation/architecture",
        "explanation/storage-model",
        "explanation/job-lifecycle",
        "explanation/discovery-provider-model",
        "explanation/export-and-pdf-model",
        "explanation/security-and-path-safety",
        "ARCHITECTURE",
        "HTTP_CLIENT",
      ],
    },
    {
      type: "category",
      label: "Project",
      items: [
        "project/contributing",
        "project/testing-guide",
        "project/wiki-maintenance",
        "project/issue-triage",
      ],
    },
  ],
};

module.exports = sidebars;
