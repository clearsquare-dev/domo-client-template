# Domo Apps Skill

Comprehensive skill for building, developing, and deploying Domo Custom Apps using React, Vite, and Domo tooling.

## What This Skill Provides

- Complete workflow guidance from project creation to deployment
- CLI command reference for `da` and `domo` tools
- Manifest configuration patterns
- AppDB/Collections usage and best practices
- API integration with @domoinc/toolkit
- Multi-environment deployment strategies
- Code examples and common patterns
- MCP tool integration for AI-assisted development (AppDB, Datasets, Code Engine, Pages, Publish)
- Dashboard and card building patterns (Beast Modes, layout, app cards)
- Code Engine serverless function templates (JS and Python)

## Skill Structure

```
domo-apps/
├── SKILL.md                        # Main skill file - always loaded
├── README.md                       # This file
├── references/                     # Detailed documentation - loaded as needed
│   ├── cli-commands.md            # Complete da and domo CLI reference
│   ├── manifest-guide.md          # Manifest.json configuration guide
│   ├── api-usage.md               # @domoinc/toolkit API patterns
│   ├── appdb.md                   # AppDB collections and queries
│   ├── deployment.md              # Multi-environment deployment
│   ├── dataset-best-practices.md  # Dataset querying and SQL patterns
│   ├── redux-state-management.md  # Redux Toolkit state management
│   ├── testing.md                 # Testing with Jest and React Testing Library
│   ├── error-handling.md          # Error handling and notifications
│   ├── form-validation.md         # Form validation patterns
│   ├── logging-analytics.md       # Domo Analytics API and logging
│   ├── mcp-tools-integration.md   # MCP tool automation for app development workflows
│   ├── dashboard-card-building.md # Dashboard cards, Beast Modes, layout, app cards
│   └── code-engine-patterns.md    # Code Engine serverless functions and templates
├── examples/                       # Example projects and patterns
│   ├── simple-app.md              # Complete task manager example
│   ├── app-with-appdb.md          # Multi-collection AppDB patterns (audit, files, preferences)
│   └── app-with-code-engine.md    # App calling Code Engine functions via package mappings
└── scripts/                        # (Reserved for future automation scripts)
```

## Usage

The skill is automatically available to Claude Code. When working on Domo Apps projects, Claude will reference:

1. **SKILL.md** - For quick reference and common workflows
2. **references/** - For detailed technical documentation
3. **examples/** - For implementation patterns

## Invoking the Skill

Users can invoke this skill with:
- `/domo-apps` - Explicit skill invocation
- Or by asking Domo-related questions naturally

## Common Use Cases

1. **New Project Setup**
   - "Create a new Domo App"
   - "Help me set up a Domo App project"

2. **Development**
   - "Generate a new component"
   - "How do I query data in a Domo App?"
   - "Add AppDB collection for storing tasks"

3. **Deployment**
   - "How do I deploy to multiple environments?"
   - "Set up deployment for dev/qa/prod"
   - "Deploy my Domo App"

4. **Troubleshooting**
   - "My manifest isn't updating"
   - "Permission denied on AppDB"
   - "Publish creates new app instead of updating"

5. **MCP-Assisted Development**
   - "Create AppDB collections for my app"
   - "Verify my dataset columns before coding"
   - "Deploy my Code Engine function"
   - "Validate and publish my app"

6. **Dashboard Integration**
   - "Place my app on a dashboard page"
   - "Create KPI cards alongside my app"
   - "Set up the page layout"

7. **Code Engine Functions**
   - "Create a serverless function for email notifications"
   - "Wire a Code Engine function to my app"
   - "Deploy a webhook handler"

## Key Features

### Progressive Disclosure
- Main SKILL.md is 171 lines (under 200-line limit)
- Detailed docs in references/ loaded only when needed
- Optimized for fast activation

### Comprehensive Coverage
- CLI commands (da and domo)
- Manifest configuration
- AppDB schemas and queries
- API integration patterns
- Multi-environment deployment
- CI/CD integration examples
- MCP tool automation for development workflows
- Dashboard and card building patterns
- Code Engine serverless function templates

### Practical Examples
- Complete task manager app
- Multi-collection AppDB patterns (audit logs, file attachments, user preferences)
- App with Code Engine backend functions (email, pricing, dataset writes)
- Redux integration
- TypeScript usage

## Maintenance

To update the skill:
1. Edit SKILL.md for common workflows (keep under 200 lines)
2. Update references/ for detailed documentation
3. Add new examples in examples/
4. Add automation scripts in scripts/

## Dependencies

This skill assumes users have:
- Node.js and yarn/npm installed
- @domoinc/da package available
- ryuu (domo CLI) package available
- Access to a Domo instance

## Version

Current version: 1.0.0
Created: 2026-02-15
