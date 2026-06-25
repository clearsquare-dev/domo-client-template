# CLI Commands Reference

Complete reference for `da` and `domo` CLI tools.

## da (Domo Apps CLI)

Development and code generation tool powered by `@domoinc/da`.

### da new

Create a new Domo App project:

```bash
# Non-interactive (recommended for automation)
echo "yarn" | da new <project-name>
echo "pnpm" | da new my-awesome-app  # pnpm is Domo's recommendation
echo "npm" | da new my-awesome-app

# Interactive (will prompt for package manager)
da new <project-name>
da new my-awesome-app

# Aliases
da n <project-name>

# Options
-f, --force      # Overwrite directory if it already exists
-m, --merge      # Merge template into existing directory
-t, --template   # Specify custom template (npm package, GitHub repo, or local path)
```

**Project Naming Requirements:**
- **MUST** use lowercase letters and hyphens only
- **Valid:** `my-app`, `sales-dashboard`, `user-analytics-v2`
- **Invalid:** `MyApp` (capitals), `my.app` (periods), `my_app` (underscores), `my@app` (symbols)

**Package Manager Selection:**
When creating a new app, you'll be prompted to select a package manager unless you pipe the selection:
- `pnpm` - Recommended by Domo
- `npm` - Standard Node package manager
- `yarn` - Popular alternative

Creates a new directory with Vite-based React template including:
- Pre-configured build setup
- Sample components
- Redux boilerplate
- Manifest template
- Proxy configuration

### da generate

Generate components or reducers:

```bash
# Interactive mode
da generate
da g

# Generate component
da generate component
da generate component MyComponent
da generate component MyComponent y n  # with test, without storybook

# Generate reducer
da generate reducer
da generate reducer myReducer
```

**Component Generation:**
- Creates component file in `src/components/`
- Optional test file
- Optional Storybook story
- Includes basic TypeScript/props setup

**Reducer Generation:**
- Creates reducer in `src/reducers/`
- Creates actions in `src/actions/`
- Auto-wires into root reducer
- Uses Redux Toolkit patterns

### da manifest

Add manifest overrides for different environments:

```bash
da manifest <identifier> [description]
da m <identifier>

# Examples
da manifest dev "Development environment"
da manifest qa "QA environment"
da manifest prod "Production environment"
```

Creates/updates `src/manifestOverrides.json`.

### da apply-manifest

Apply manifest overrides before start or build:

```bash
da apply-manifest <phase> [environment]
da am <phase> [environment]

# Apply for development
da apply-manifest start
da apply-manifest start dev

# Apply for build
da apply-manifest build
da apply-manifest build prod
da apply-manifest build "domo-es.dev"
```

Typically used in package.json scripts:
```json
{
  "prestart": "da apply-manifest start",
  "postbuild": "da apply-manifest build prod"
}
```

### da build-replacements

Apply build-time string replacements (if configured):

```bash
da build-replacements
```

Used in CI/CD pipelines for environment-specific string replacements.

## domo (Ryuu CLI)

Deployment and management tool powered by `ryuu` package.

### domo login

Authenticate to Domo instance:

```bash
domo login
domo login -i <instance>
domo login -i company.domo.com
domo login --no-upgrade-check
domo login -f "./public/manifest.json"

# Options
-i, --instance <instance>  # Domo instance URL
-f, --manifest <path>      # Path to manifest
--no-upgrade-check         # Skip version check
```

Stores credentials for subsequent commands.

### domo logout

Log out of Domo:

```bash
domo logout
```

### domo publish

Publish app to Domo:

```bash
domo publish
domo publish -m ./manifest.json

# Options
-m, --manifest <path>  # Path to manifest
```

**Workflow:**
1. Build your app: `yarn build`
2. Navigate to build folder: `cd build`
3. Publish: `domo publish`
4. Navigate back: `cd ..`

**First Publish:**
- Creates new app in Domo
- Generates app `id` in manifest
- Copy `id` to your source manifest to prevent creating new app

### domo init

Initialize a new Custom App design:

```bash
domo init
domo init -n "My App"

# Options
-n, --name <name>  # App name
```

### domo dev

Run local development server:

```bash
domo dev
domo dev -p 3000

# Options
-p, --port <port>  # Port number
```

Alternative to `yarn start` - runs Ryuu dev server.

### domo ls

List all your Custom App designs:

```bash
domo ls
domo ls --all

# Options
--all  # Include soft-deleted apps
```

Shows app IDs, names, and versions.

### domo download

Download an existing app:

```bash
domo download
domo download -i <app-id>

# Options
-i, --id <id>  # App ID to download
```

Downloads app assets and manifest to current directory.

### domo delete

Soft delete an app:

```bash
domo delete <app-id>
domo delete 1234567890
```

App can be restored with `domo undelete`.

### domo undelete

Restore a soft-deleted app:

```bash
domo undelete <app-id>
```

### domo owner

Manage app owners:

```bash
# List owners
domo owner ls <app-id>

# Add owner
domo owner add <app-id> user@example.com

# Remove owner
domo owner rm <app-id> user@example.com
```

### domo token

Manage developer tokens:

```bash
domo token add
domo token rm
```

### domo proxy

Configure proxy settings:

```bash
domo proxy <host> <port>
domo proxy proxy.company.com 8080
```

### domo remove

Remove instance from login list:

```bash
domo remove
```

### domo release

Prepare design for app store release:

```bash
domo release
```

## Common Workflows

### First Time Setup

```bash
# Non-interactive (automated)
echo "yarn" | da new my-app
cd my-app
domo login -i company.domo.com
yarn start

# Or interactive
da new my-app  # Select package manager when prompted
cd my-app
yarn install
domo login -i company.domo.com
yarn start
```

### Development Cycle

```bash
# Terminal 1: Development
yarn start

# Make changes...

# Terminal 2: Deploy
yarn build
cd build
domo publish
cd ..
```

### Generate New Feature

```bash
da generate component FeatureName y y  # with test and storybook
da generate reducer feature
# Implement feature...
```

### Multi-Environment Deploy

```bash
# Build for QA
yarn build:qa
da apply-manifest build qa
cd build

# Login to QA instance
domo login -i company-qa.domo.com

# Publish
domo publish
cd ..
```

### Switch Instances

```bash
# Login to different instance
domo login -i another-company.domo.com

# Deploy to new instance
cd build && domo publish && cd ..
```

## Tips

1. **Project Naming** - Project names must use lowercase and hyphens only (e.g., `my-domo-app`). No capitals, periods, underscores, or other symbols allowed

2. **First Deploy** - After first `domo publish`, copy the `id` field from `build/manifest.json` to `public/manifest.json`

3. **Quick Upload** - Use package script:
   ```json
   "upload": "yarn build && cd build && domo publish && cd .."
   ```

4. **Manifest Sync** - Always run `da apply-manifest` before build in different environments

5. **Stay Logged In** - `domo login` persists, no need to login each time

6. **List Apps** - Use `domo ls` to find app IDs

7. **Version Control** - Don't commit the `id` field if sharing starter templates

8. **Multiple Instances** - Can stay logged into multiple instances simultaneously
