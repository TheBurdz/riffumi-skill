# Submitting the Riffumi plugin to the directories

Two portals, one package. Both take a skills-only plugin; neither needs an MCP server, test
cases or a demo video for this kind of plugin. Written 2026-11-14 against the published docs
linked below; check the portal if a step looks different.

## Before either portal

- `./build.sh` passes, `claude plugin validate . --profile directory` passes, and the smoke test
  renders from `skills/riffumi`.
- `version` in `plugin.json` and `.claude-plugin/plugin.json` is raised (they must match), the
  release is tagged `v<version>` with `dist/riffumi-skill.zip` attached, and the zip is copied
  into the Riffumi site (see the site's `docs/SKILL_EDITION.md`).
- The repository is public (it is), the README at the root describes everything the skill runs,
  fetches and sends (it does), `LICENSE` is at the root (MIT).

## Claude plugin directory

Portal: https://claude.ai/directory/manage (paid Claude plan; connect the GitHub account that can
push to `TheBurdz/riffumi-skill` when the portal asks).

1. **Submit new**, then **Plugin bundle**.
2. Source: repository `TheBurdz/riffumi-skill`, plugin path empty (the manifest is at the root),
   branch or tag `main` (or a release tag to publish only tagged versions).
3. **Validate**. Fix anything marked Blocking, push, **Re-validate**. Expected findings:
   - Warnings about external fetches (fonts, pexels.com downloads, pip installs). They are
     disclosed in the README under "What the skill runs, fetches and sends".
   - Possibly a policy hold on media content. The statement for the reviewer: Riffumi edits the
     user's own clips and photos. It generates no footage, no faces and no voices. Stock b-roll
     comes from pexels.com under the Pexels License with source and creator logged. Transcription
     runs locally.
4. **Listing details** come from `plugin.json` and the README; edit those files, not the form.
5. **Data handling** answers: reads personal data: no (it reads files the user hands it, on the
   user's machine); sends data to services other than declared connectors: only the fetches
   listed in the README (Google Fonts, GitHub raw for fonts, pexels.com for stock, pypi.org for
   the two packages); keeps data: nothing, there is no server; intended for people under 18: no.
6. **Compliance**: contact email support@riffumi.com, tick the four acknowledgements.
7. **Review and submit**: keep the GitHub push webhook on so new commits on the tracked branch
   are picked up; set it up when the portal offers (needs admin on the repository).
8. When the version passes, **Publish**. A reviewer publishes the first version.

After approval the plugin's **Usage** tab shows installs, versions, runs and error rates.

Docs: https://claude.com/docs/plugins/submit and
https://claude.com/docs/plugins/pre-submission-checklist. Policy:
https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy.

## OpenAI plugin directory (ChatGPT and Codex)

Portal: https://platform.openai.com/plugins (the organisation that holds the verified identity;
the plugin publishes under that verified name, so either complete business verification for
The Burdz, LLC first or set `author.name` and `developerName` to the verified individual's
name before uploading).

1. **Create plugin**, then **Skills only**.
2. Upload `dist/riffumi-plugin.zip` (built by `./build.sh`; it holds `plugin.json`,
   `.claude-plugin/plugin.json`, `skills/`, `README.md`, `LICENSE`, `assets/`).
3. Review the generated `.codex-plugin/plugin.json`; the listing fields come from
   `extensions.com.openai.interface` in `plugin.json` (display name and subtitle are under 30
   characters, the long description under 4,000).
4. Fix every scan finding, complete the listing, submit. Skills-only plugins need no MCP review
   cases and no demo recording; release notes live in the package.
5. Expect a question about local execution: the submission guide asks developers to talk to an
   OpenAI partner when a plugin's core value depends on running code locally or offline. The
   answer is in the README: the skill is a set of plain Python scripts and ffmpeg calls, with the
   hosted connector at riffumi.com as the no-code alternative.

Do not include `.mcp.json`, hooks, commands or agents in the archive (none are present). Keep
Claude product names out of instructions unless they truly apply (SKILL.md has none; the host
table in the skill README names hosts factually).

Docs: https://developers.openai.com/plugins/deploy/submission,
https://developers.openai.com/plugins/guides/submit-claude-plugin,
https://developers.openai.com/codex/plugins/build.

## Listing copy (shared)

- Display name: `Riffumi`
- Subtitle: `Direct videos from your own clips`
- Category: Productivity
- Long description: the `longDescription` in `plugin.json`.
- Icon and logo: `assets/icon.png`, `assets/logo.png` (512 x 512 PNG).
- Links: https://riffumi.com/skill, https://riffumi.com/help, https://riffumi.com/privacy,
  https://riffumi.com/terms.

## Releasing an update

Raise `version` in both manifests, commit, tag `v<version>`, `./build.sh`, attach
`dist/riffumi-skill.zip` and `dist/riffumi-plugin.zip` to the release, copy the skill zip into the
site. The Claude listing follows the tracked branch on its own; the OpenAI listing takes a new
archive upload.
