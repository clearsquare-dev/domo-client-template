# Domo API Usage Guide

Real-world patterns for using `@domoinc/toolkit`, `@domoinc/query`, and `ryuu.js` to interact with Domo APIs.

## Installation

```bash
yarn add @domoinc/toolkit @domoinc/query ryuu.js
```

## Key Libraries

- **`@domoinc/query`** - Query class for fetching dataset data
- **`@domoinc/toolkit`** - Typed clients for Identity, Users, SQL, AppDB
- **`ryuu.js`** - General API calls, file operations, package functions

## Querying Datasets

### Using Query Class (Recommended)

```typescript
import Query from '@domoinc/query';

// Simple query
const data = await new Query()
  .select(['column1', 'column2', 'column3'])
  .fetch<MyDataType>('DatasetAlias');

// With type safety
const SCHEMA = ['WorkItemType', 'DataSetId'] as const;
const results = await new Query()
  .select(SCHEMA)
  .fetch<Record<typeof SCHEMA[number], string>>('DataSourceRegistry');

// Transform results
const registry = results.reduce((acc, row) => ({
  ...acc,
  [row.WorkItemType]: row.DataSetId,
}), {});
```

### Using SqlClient

```typescript
import { SqlClient } from '@domoinc/toolkit';

const query = `
  SELECT "Column1", "Column2", "Column3"
  FROM table
  WHERE "Status" = 'Active'
  ORDER BY "CreatedDate" DESC
  LIMIT 100
`;

const { data: result } = await new SqlClient().get('DatasetAlias', query);

// Result structure: { columns: string[], rows: any[][] }
const mappedData = result.rows.map(row =>
  result.columns.reduce((obj, col, idx) => ({
    ...obj,
    [col]: row[idx]
  }), {})
);
```

### Using Direct Fetch with SQL

```typescript
const executeSQL = async (datasetId: string, query: string) => {
  const response = await fetch(`/domo/query/v1/execute/${datasetId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'accept': 'application/json',
    },
    body: JSON.stringify({ sql: query }),
  });
  return await response.json();
};

// Usage
const query = `
  SELECT "UID", "Status", "Owner"
  FROM table
  WHERE "UID" IN ('uid1', 'uid2', 'uid3')
`;
const result = await executeSQL(datasetId, query);
```

## User & Identity

### Get Current User

```typescript
import { IdentityClient, UserClient } from '@domoinc/toolkit';

// Get current identity
const identity = (await IdentityClient.get(undefined, true)).data;
console.log(identity.userId); // Current user ID

// Get user details
const user = (await UserClient.getUser(identity.userId)).data;
console.log(user.displayName, user.email, user.role);
```

### Check User Permissions

```typescript
import { IdentityClient } from '@domoinc/toolkit';

const loadUserInfo = async () => {
  const identity = (await IdentityClient.get(undefined, true)).data;
  const user = (await UserClient.getUser(identity.userId)).data;

  // Check grants
  const url = '/domo/roles/v1/authorities/me';
  const res = await fetch(url);
  const grants = await res.json();

  const hasEditPermission = grants?.includes('edit-dataset');
  const isAdmin = user?.role?.toLowerCase() === 'admin';

  return { identity, user, hasEditPermission, isAdmin };
};
```

## AppDB Collections

### Create Typed Client

```typescript
import { AppDBClient, AppDBDocument } from '@domoinc/toolkit';

// Define your data type
interface LogEntry {
  entryId: string;
  UID: string;
  field: string;
  value: string;
}

// Create typed client for collection
const AuditLogClient = new AppDBClient.DocumentsClient<LogEntry>(
  'EXM_Audit_Log'
);
```

### Query Documents

```typescript
// Get all documents
const response = await AuditLogClient.get({}, {});
const allDocs = response.data;

// Query with filters
const queryParams = {
  'content.UID': { $eq: 'specific-uid' },
  'content.status': { $in: ['Active', 'Pending'] },
};
const options = {
  orderby: ['createdOn descending'],
  limit: 100,
};
const docs = (await AuditLogClient.get(queryParams, options)).data;

// Query multiple UIDs
const uidList = ['uid1', 'uid2', 'uid3'];
const subscriptions = await SubscriptionClient.get({
  'content.UID': { $in: uidList },
  'content.userEmail': { $eq: userEmail },
});
```

### Create Documents

```typescript
// Create single document
const newDoc = await AuditLogClient.create({
  entryId: '123',
  UID: 'user-456',
  field: 'status',
  value: 'completed',
});

// Create multiple documents
const logs: LogEntry[] = [
  { entryId: '1', UID: 'uid1', field: 'status', value: 'new' },
  { entryId: '2', UID: 'uid2', field: 'priority', value: 'high' },
];
await AuditLogClient.create(logs);

// Batch create with loop
const uids = ['uid1', 'uid2', 'uid3'];
const docs = uids.map(uid => ({ UID: uid, userEmail: email }));
await SubscriptionClient.create(docs);
```

### Update Documents

```typescript
// Update by ID
await AuditLogClient.update(documentId, {
  entryId: '123',
  UID: 'user-456',
  field: 'status',
  value: 'updated',
});
```

### Delete Documents

```typescript
// Delete single document
await AuditLogClient.delete(documentId);

// Delete multiple documents
const idsToDelete = ['doc-id-1', 'doc-id-2', 'doc-id-3'];
await SubscriptionClient.delete(idsToDelete);
```

### Extract Document Data

```typescript
// Helper to extract content from AppDB response
const extractAppDbData = <T>(response: { data: AppDBDocument<T>[] }): T[] =>
  response.data.map(doc => ({
    id: doc.id,
    ...doc.content,
  }));

// Usage
const subscriptions = extractAppDbData<Subscription>(
  await SubscriptionClient.get(queryParams)
);
```

### Load with User Details

```typescript
import { AppDBClient, UserClient } from '@domoinc/toolkit';

const loadChangeLog = async (uid: string) => {
  const queryParams = { 'content.UID': { $eq: uid } };
  const options = { orderby: ['createdOn descending'] };

  const logs = (await AuditLogClient.get(queryParams, options)).data;

  // Collect unique user IDs
  const userIds = new Set<string>();
  logs.forEach(log => userIds.add(log.owner.toString()));

  // Fetch user names
  const userNameMap = (
    await Promise.all(
      Array.from(userIds).map(id => UserClient.getUser(parseInt(id, 10)))
    )
  ).reduce((acc, next) => {
    acc[next.data.id.toString()] = next.data.displayName;
    return acc;
  }, {} as Record<string, string>);

  return { logs, userNameMap };
};
```

## File Operations

### Upload File to Domo

```typescript
import domo from 'ryuu.js';

const uploadFile = async (file: File, description = '', isPublic = false) => {
  const formData = new FormData();
  formData.append('file', file);

  const url = `/domo/data-files/v1?name=${encodeURIComponent(file.name)}&description=${encodeURIComponent(description)}&public=${isPublic}`;

  const options = { contentType: 'multipart' };

  return domo.post(url, formData, options);
};
```

### Download File from Domo

```typescript
import domo from 'ryuu.js';
import Download from 'downloadjs';

const downloadFile = async (fileId: string, filename: string) => {
  const url = `/domo/files/v1/${fileId}`;
  const options = { responseType: 'blob' as XMLHttpRequestResponseType };

  const fileData = await domo.get<Blob>(url, options);
  Download(fileData, filename);
};
```

## Package Mappings (Code Engine)

### Call Package Functions

```typescript
import domo from 'ryuu.js';

const CODE_ENGINE_BASE_URL = '/domo/codeengine/v2/packages';

// Send email via package
const sendEmail = async (email: EmailParams) => {
  const { returnValue } = await domo.post<{
    returnValue: { statusCode: number; payload: string };
  }>(`${CODE_ENGINE_BASE_URL}/sendEmail`, {
    params: {
      to: email.to,
      subject: email.subject,
      body: email.body,
      cc: email.cc,
      attachments: email.attachments,
    },
  });

  if (returnValue.statusCode !== 200) {
    throw new Error('Email cannot be sent');
  }
};

// Invoke workflow via package
const invokeWorkflow = async (
  workflowId: string,
  workflowVersion: string,
  workflowParams: Record<string, any>
) => {
  const response = await domo.post<{
    returnValue: { status: boolean; error?: string };
  }>(`${CODE_ENGINE_BASE_URL}/invokeWorkflow`, {
    params: {
      workflowId,
      workflowVersion,
      workflowParams,
    },
  });

  return response.returnValue;
};

// Get file from external system
const getFile = async (fileParams: FileParams) => {
  const { returnValue } = await domo.post<{
    returnValue: {
      statusCode: number;
      file: { content: string; headers: Record<string, string> };
    };
  }>(`${CODE_ENGINE_BASE_URL}/getFile`, {
    params: fileParams,
  });

  if (returnValue.statusCode !== 200) {
    throw new Error('File not found');
  }

  return returnValue.file;
};
```

## Data Upload (Dataset Update)

### Upload Data with Retry

```typescript
const insertOrUpdateData = async (
  datasetId: string,
  csvContent: string,
  maxRetries: number = 3
) => {
  // Modern approach (v4)
  return await fetch(
    `/api/data/v3/datasources/${datasetId}/executions/upload?updateMethod=UPSERT`,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: csvContent,
    }
  );
};

// Helper to convert data to CSV
const dataToCSVString = (data: Record<string, string>): string =>
  Object.values(data)
    .map(value => `"${value.replaceAll('"', '""')}"`)
    .join(',');

// Usage
const updatedData = {
  UID: 'uid-123',
  Status: 'Completed',
  Owner: 'john@example.com',
  LastUpdated: new Date().toISOString(),
};

const csvRow = dataToCSVString(updatedData);
await insertOrUpdateData(datasetId, csvRow);
```

### Batch Upload

```typescript
const submitBulkEdit = async (
  datasetId: string,
  dataToUpdate: Record<string, any>[]
) => {
  // Convert each row to CSV format
  const csvRows = dataToUpdate.map(row => dataToCSVString(row));

  // Combine into single CSV content
  const csvContent = csvRows.join('\n');

  // Upload
  return await insertOrUpdateData(datasetId, csvContent);
};
```

## Error Handling & Retry

### Retry Pattern

```typescript
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const withRetry = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 1000
): Promise<T> => {
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (attempt < maxRetries - 1) {
        const delayMs = baseDelayMs * Math.pow(2, attempt); // Exponential backoff
        console.warn(
          `Attempt ${attempt + 1} failed, retrying in ${delayMs}ms...`,
          lastError.message
        );
        await sleep(delayMs);
      }
    }
  }

  throw lastError;
};

// Usage
const data = await withRetry(
  () => AuditLogClient.get(queryParams),
  3,
  1000
);
```

### Fetch with Retry

```typescript
const fetchWithRetry = async (
  url: string,
  options: RequestInit,
  maxRetries: number = 3
): Promise<Response> =>
  withRetry(
    async () => {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      return response;
    },
    maxRetries,
    1000
  );
```

## Real-World Service Pattern

```typescript
import Query from '@domoinc/query';
import {
  AppDBClient,
  IdentityClient,
  SqlClient,
  UserClient,
} from '@domoinc/toolkit';
import domo from 'ryuu.js';

// Define types
interface LogEntry {
  entryId: string;
  UID: string;
  field: string;
  value: string;
}

// Create clients
const AuditLogClient = new AppDBClient.DocumentsClient<LogEntry>(
  'EXM_Audit_Log'
);

// Service methods
export const StorageService = {
  // Load user identity
  async loadUserInfo() {
    const identity = (await IdentityClient.get(undefined, true)).data;
    const user = (await UserClient.getUser(identity.userId)).data;
    return { identity, user };
  },

  // Query dataset with Query class
  async loadRegistry() {
    const SCHEMA = ['WorkItemType', 'DataSetId'] as const;
    return await new Query()
      .select(SCHEMA)
      .fetch<Record<typeof SCHEMA[number], string>>('DataSourceRegistry');
  },

  // AppDB operations
  async createAuditLogs(logs: LogEntry[]) {
    return await AuditLogClient.create(logs);
  },

  async loadChangeLog(uid: string) {
    const queryParams = { 'content.UID': { $eq: uid } };
    const options = { orderby: ['createdOn descending'] };
    const logs = (await AuditLogClient.get(queryParams, options)).data;
    return logs;
  },

  // SQL query
  async fetchEntryData(columns: string[], ids: string[]) {
    const query = `
      SELECT ${columns.map(col => `"${col}"`).join(',')}
      FROM EntryData
      WHERE UID IN (${ids.map(uid => `'${uid}'`).join(',')})
    `;
    const { data: result } = await new SqlClient().get('EntryData', query);
    return result;
  },

  // File upload
  async uploadFile(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const url = `/domo/data-files/v1?name=${encodeURIComponent(file.name)}&public=false`;
    return await domo.post(url, formData, { contentType: 'multipart' });
  },

  // Package call
  async sendEmail(emailParams: any) {
    return await domo.post('/domo/codeengine/v2/packages/sendEmail', {
      params: emailParams,
    });
  },
};
```

## TypeScript Best Practices

### Define Interfaces

```typescript
// AppDB document type
interface Subscription {
  id?: string;
  UID: string;
  userEmail: string;
}

// AppDB document with metadata
interface LogEntryDocument extends AppDBDocument<LogEntry> {
  id: string;
  owner: string;
  createdOn: string;
  updatedOn: string;
}

// API response type
interface WorkflowResponse {
  returnValue: {
    status: boolean;
    error?: string;
    data?: any;
  };
}
```

### Use Type-Safe Constants

```typescript
// Dataset aliases
export const DATASET_ALIASES = {
  DataSourceRegistry: 'DataSourceRegistry',
  EntryData: 'EntryData',
  CoreFields: 'CoreFields',
} as const;

// Collection names
export const COLLECTION_NAMES = {
  AuditLog: 'EXM_Audit_Log',
  Comments: 'EXM_Comments',
  Files: 'EXM_Files_Details',
} as const;

// Schema definitions
export const DATASOURCE_REGISTRY_SCHEMA = [
  'WorkItemType',
  'DataSetId',
] as const;
```

## Best Practices

1. **Use Typed Clients** - Create `AppDBClient.DocumentsClient<T>` instances for type safety
2. **Query Class** - Prefer `@domoinc/query` Query class for dataset queries
3. **ryuu.js for General API** - Use `domo` from `ryuu.js` for file ops and package calls
4. **Error Handling** - Always wrap API calls in try/catch with retry logic
5. **Extract Helper** - Create `extractAppDbData` helper to simplify AppDB responses
6. **Type Safety** - Define TypeScript interfaces for all data structures
7. **Constants** - Use `as const` for dataset aliases and collection names
8. **Batch Operations** - Group related API calls to minimize requests
9. **Exponential Backoff** - Use exponential backoff for retry logic
10. **Service Pattern** - Organize API calls into service modules
