# Domo Apps Skill - Installation Guide

Install this skill to add Domo App development capabilities to Claude Code.

## Installation Methods

### Method 1: Direct Copy (Recommended)

1. Copy the skill directory to your Claude skills folder:

```bash
# If you have the skill directory
cp -r domo-apps ~/.claude/skills/

# Or clone from git (if hosted)
git clone https://github.com/your-org/claude-skill-domo-apps.git ~/.claude/skills/domo-apps
```

2. Restart Claude Code or reload the window

3. Verify installation:
   - The skill should appear in your available skills list
   - Try invoking with `/domo-apps`

### Method 2: From Archive

1. Download the skill archive:
   - `domo-apps-skill.tar.gz` or `domo-apps-skill.zip`

2. Extract to Claude skills directory:

```bash
# For .tar.gz
tar -xzf domo-apps-skill.tar.gz -C ~/.claude/skills/

# For .zip
unzip domo-apps-skill.zip -d ~/.claude/skills/
```

3. Restart Claude Code

### Method 3: Git Submodule (For Team Use)

If managing skills in a shared repository:

```bash
cd ~/.claude/skills
git submodule add https://github.com/your-org/claude-skill-domo-apps.git domo-apps
git submodule update --init --recursive
```

## Verification

After installation, the skill should appear in the available skills list:

```
domo-apps: Build, develop, and deploy Domo Custom Apps using React, Vite, and Domo tooling
```

Test it by asking Claude:
- "How do I create a new Domo App?"
- "Help me with Domo App deployment"

## Prerequisites

This skill assumes you have:
- Node.js (v16+) and yarn/npm installed
- `@domoinc/da` package available
- `ryuu` (domo CLI) package available
- Access to a Domo instance

## Updating

To update the skill:

```bash
cd ~/.claude/skills/domo-apps
git pull origin main  # if using git
# or replace the directory with new version
```

## Uninstallation

```bash
rm -rf ~/.claude/skills/domo-apps
```

Then restart Claude Code.

## Troubleshooting

**Skill not appearing:**
- Ensure the directory is at `~/.claude/skills/domo-apps`
- Check that `SKILL.md` exists in the directory
- Restart Claude Code
- Check the YAML frontmatter in SKILL.md is valid

**Skill not activating:**
- Try invoking explicitly with `/domo-apps`
- Check Claude Code logs for errors
- Verify file permissions (should be readable)

## Support

For issues or questions:
- Check the README.md in the skill directory
- Review the reference documentation in `references/`
- Open an issue on GitHub (if applicable)

## License

[Add your license information here]
