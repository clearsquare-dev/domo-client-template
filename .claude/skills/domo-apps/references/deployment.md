# Deployment Guide

Strategies for deploying Domo Apps across multiple environments.

## Quick Deploy

```bash
# Build and publish in one command
yarn upload

# Or manually
yarn build
cd build
domo publish
cd ..
```

## Multi-Environment Setup

### Environment Configuration

Create `deploy.js` in project root:

```javascript
const { execSync } = require('child_process');
const inquirer = require('inquirer');

const environments = {
  'dev': {
    mapping: 'development',
    instance: 'company-dev.domo.com',
  },
  'qa': {
    mapping: 'qa',
    instance: 'company-qa.domo.com',
  },
  'prod': {
    mapping: 'production',
    instance: 'company.domo.com',
  },
};

const environmentList = Object.keys(environments);

inquirer
  .prompt([
    {
      type: 'list',
      name: 'environment',
      message: 'Select an environment:',
      choices: environmentList,
    },
  ])
  .then((answers) => {
    const selectedEnvironment = answers['environment'];
    const env = environments[selectedEnvironment];

    // Login
    console.log(`Logging in to ${env.instance}...`);
    execSync(
      `domo login -i ${env.instance} --no-upgrade-check`,
      { stdio: 'inherit' }
    );

    // Build
    console.log(`Building for ${env.mapping}...`);
    execSync(`yarn build:${env.mapping}`, { stdio: 'inherit' });

    // Apply manifest
    console.log(`Applying manifest...`);
    execSync(`da apply-manifest build ${env.mapping}`, { stdio: 'inherit' });

    // Publish
    console.log(`Publishing...`);
    execSync(`cd build && domo publish && cd ..`, { stdio: 'inherit' });

    console.log(`✓ Deployed to ${env.instance}`);
  })
  .catch((error) => {
    console.error('Deployment failed:', error);
  });
```

### Package Scripts

Add to `package.json`:

```json
{
  "scripts": {
    "deploy": "node deploy.js",
    "build:dev": "REACT_APP_TARGET=development react-scripts build",
    "build:qa": "REACT_APP_TARGET=qa react-scripts build",
    "build:prod": "GENERATE_SOURCEMAP=false REACT_APP_TARGET=production react-scripts build",
    "postbuild:dev": "da apply-manifest build development",
    "postbuild:qa": "da apply-manifest build qa",
    "postbuild:prod": "da apply-manifest build production"
  }
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Domo

on:
  push:
    branches: [main, develop]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Setup Node
        uses: actions/setup-node@v2
        with:
          node-version: '18'

      - name: Install Dependencies
        run: yarn install

      - name: Build
        run: yarn build:${{ github.ref == 'refs/heads/main' && 'prod' || 'dev' }}
        env:
          GENERATE_SOURCEMAP: false

      - name: Apply Manifest
        run: da apply-manifest build ${{ github.ref == 'refs/heads/main' && 'production' || 'development' }}

      - name: Login to Domo
        run: domo login -i ${{ secrets.DOMO_INSTANCE }} -t ${{ secrets.DOMO_TOKEN }}

      - name: Publish
        run: cd build && domo publish && cd ..
```

### Jenkins Pipeline

```groovy
pipeline {
  agent any

  environment {
    DOMO_INSTANCE = credentials('domo-instance')
    DOMO_TOKEN = credentials('domo-token')
  }

  stages {
    stage('Install') {
      steps {
        sh 'yarn install'
      }
    }

    stage('Build') {
      steps {
        script {
          def env = BRANCH_NAME == 'main' ? 'prod' : 'dev'
          sh "yarn build:${env}"
          sh "da apply-manifest build ${env}"
        }
      }
    }

    stage('Deploy') {
      steps {
        sh "domo login -i ${DOMO_INSTANCE} -t ${DOMO_TOKEN}"
        sh 'cd build && domo publish && cd ..'
      }
    }
  }
}
```

## Manifest Overrides

Use `src/manifestOverrides.json` for environment-specific configs:

```json
{
  "development": {
    "mapping": [
      {
        "dataSetId": "dev-dataset-id",
        "alias": "MyData"
      }
    ],
    "collections": [
      {
        "name": "DevCollection"
      }
    ]
  },
  "qa": {
    "mapping": [
      {
        "dataSetId": "qa-dataset-id",
        "alias": "MyData"
      }
    ]
  },
  "production": {
    "mapping": [
      {
        "dataSetId": "prod-dataset-id",
        "alias": "MyData"
      }
    ]
  }
}
```

## Environment Variables

Use `.env` files for environment-specific settings:

**.env.development:**
```bash
REACT_APP_API_URL=https://dev-api.example.com
REACT_APP_FEATURE_FLAGS={"newFeature":true}
```

**.env.production:**
```bash
REACT_APP_API_URL=https://api.example.com
REACT_APP_FEATURE_FLAGS={"newFeature":false}
```

**Usage in code:**
```typescript
const apiUrl = process.env.REACT_APP_API_URL;
```

## Version Management

Update version in manifest before deployment:

```bash
# Manually edit public/manifest.json
{
  "version": "1.2.3"
}

# Or use npm version
npm version patch  # 1.0.0 -> 1.0.1
npm version minor  # 1.0.0 -> 1.1.0
npm version major  # 1.0.0 -> 2.0.0
```

## Rollback Strategy

1. **Keep Previous Builds**
   ```bash
   mv build build-v1.2.3
   ```

2. **Use Git Tags**
   ```bash
   git tag v1.2.3
   git push --tags
   ```

3. **Rollback**
   ```bash
   git checkout v1.2.2
   yarn install
   yarn build:prod
   cd build && domo publish && cd ..
   ```

## Pre-Deployment Checklist

- [ ] Update version in manifest.json
- [ ] Run tests: `yarn test:ci`
- [ ] Lint code: `yarn lint`
- [ ] Build succeeds: `yarn build:prod`
- [ ] Review manifest changes
- [ ] Verify environment variables
- [ ] Test in QA first
- [ ] Update changelog
- [ ] Create git tag

## Best Practices

1. **Never Deploy Directly to Prod** - Always test in QA first
2. **Use Manifest Overrides** - Keep environment configs separate
3. **Disable Source Maps in Prod** - Set `GENERATE_SOURCEMAP=false`
4. **Version Control** - Tag releases in git
5. **Automate** - Use CI/CD pipelines for consistency
6. **Monitor** - Check app after deployment
7. **Communicate** - Notify users of deployments
8. **Document** - Keep deployment notes
