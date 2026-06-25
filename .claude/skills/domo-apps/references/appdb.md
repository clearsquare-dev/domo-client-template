# AppDB (Collections) Guide

AppDB provides local database storage for your Domo Custom App using MongoDB-style collections.

## What is AppDB?

AppDB is a NoSQL database built into Domo Apps that allows you to:
- Store application state across sessions
- Create user-specific data
- Build collaborative features
- Implement audit logs and comments
- Store file metadata

## Defining Collections

Collections are defined in `manifest.json`:

```json
{
  "collections": [
    {
      "name": "Tasks",
      "syncEnabled": true,
      "schema": {
        "columns": [
          {
            "name": "title",
            "type": "STRING"
          },
          {
            "name": "completed",
            "type": "STRING"
          },
          {
            "name": "dueDate",
            "type": "STRING"
          },
          {
            "name": "priority",
            "type": "STRING"
          }
        ]
      },
      "defaultPermission": [
        "READ",
        "READ_CONTENT",
        "CREATE_CONTENT",
        "UPDATE_CONTENT",
        "DELETE_CONTENT"
      ]
    }
  ]
}
```

## Data Types

**IMPORTANT:** Always use `STRING` for all column types. Other types (`NUMBER`, `BOOLEAN`, `DATE`) are **not supported** by the Domo AppDB API and will cause publish errors. Store all values as strings and convert in your application code.

## Permissions

### Permission Levels

- **READ** - List/query documents (required to see documents exist)
- **READ_CONTENT** - Read document content
- **CREATE_CONTENT** - Insert new documents
- **UPDATE_CONTENT** - Modify existing documents
- **DELETE_CONTENT** - Remove documents

### Permission Patterns

**Public Read, User Write:**
```json
{
  "defaultPermission": ["READ", "READ_CONTENT"],
  "filters": [
    {
      "name": "UserWrite",
      "applyOn": ["CREATE", "UPDATE", "DELETE"],
      "applyTo": [],
      "applyToAll": true,
      "limitToOwner": true,
      "query": {}
    }
  ]
}
```

**User-Specific Data:**
```json
{
  "defaultPermission": ["CREATE_CONTENT"],
  "filters": [
    {
      "name": "UserData",
      "applyOn": ["READ", "UPDATE", "DELETE"],
      "applyTo": [],
      "applyToAll": true,
      "limitToOwner": true,
      "query": {}
    }
  ]
}
```

**Admin Only:**
```json
{
  "defaultPermission": [],
  "filters": [
    {
      "name": "AdminOnly",
      "applyOn": ["READ", "CREATE", "UPDATE", "DELETE"],
      "applyTo": ["admin@company.com"],
      "applyToAll": false,
      "limitToOwner": false,
      "query": {}
    }
  ]
}
```

## Setting Up Typed Clients

Always create typed clients for type safety:

```typescript
import { AppDBClient, AppDBDocument } from '@domoinc/toolkit';

// Define your data types
interface TaskData {
  title: string;
  completed: boolean;
  dueDate: string;
  priority: number;
}

interface LogEntryData {
  entryId: string;
  UID: string;
  field: string;
  value: string;
}

interface CommentData {
  UID: string;
  userEmail: string;
  userName: string;
  body: string;
  attachment?: string;
  systemGenerated?: string;
}

// Create typed clients
const TasksClient = new AppDBClient.DocumentsClient<TaskData>('Tasks');
const AuditLogClient = new AppDBClient.DocumentsClient<LogEntryData>('EXM_Audit_Log');
const CommentsClient = new AppDBClient.DocumentsClient<CommentData>('EXM_Comments');
```

### Helper to Extract Document Content

```typescript
const extractAppDbData = <T>(response: { data: AppDBDocument<T>[] }): (T & { id: string })[] =>
  response.data.map(doc => ({
    id: doc.id,
    ...doc.content,
  }));
```

## CRUD Operations

### Create (Insert)

```typescript
// Create single document
const newTask = await TasksClient.create({
  title: 'My Task',
  completed: false,
  dueDate: '2024-12-31T23:59:59Z',
  priority: 1,
});

// Extract with ID
const task = extractAppDbData<TaskData>(newTask)[0];
console.log(task.id); // Auto-generated document ID

// Create multiple documents
const logs: LogEntryData[] = [
  { entryId: '1', UID: 'uid-1', field: 'status', value: 'new' },
  { entryId: '2', UID: 'uid-2', field: 'priority', value: 'high' },
];
await AuditLogClient.create(logs);

// Batch create from array
const uids = ['uid-1', 'uid-2', 'uid-3'];
const subscriptions = uids.map(uid => ({ UID: uid, userEmail: 'user@example.com' }));
await SubscriptionClient.create(subscriptions);
```

### Read (Query)

```typescript
// Get all documents
const response = await TasksClient.get({}, {});
const allTasks = response.data; // AppDBDocument<TaskData>[]

// Get with extracted content
const tasks = extractAppDbData<TaskData>(await TasksClient.get({}, {}));

// Query with equality filter
const queryParams = {
  'content.completed': { $eq: false },
};
const incompleteTasks = (await TasksClient.get(queryParams, {})).data;

// Query with multiple filters
const filtered = (await TasksClient.get({
  'content.priority': { $gte: 3 },
  'content.completed': { $eq: false },
}, {})).data;

// Query with IN operator
const specific = (await AuditLogClient.get({
  'content.UID': { $in: ['uid-1', 'uid-2', 'uid-3'] },
}, {})).data;

// Query with ordering
const sorted = (await AuditLogClient.get(
  { 'content.UID': { $eq: 'uid-1' } },
  { orderby: ['createdOn descending'] }
)).data;

// Query with limit
const limited = (await TasksClient.get(
  {},
  { limit: 10 }
)).data;

// Query with groupby
const grouped = (await FilesClient.get(
  { 'content.UID': { $in: uidList } },
  { groupby: ['content.UID'] }
)).data;
```

### Update

```typescript
// Update by document ID
await TasksClient.update(documentId, {
  title: 'Updated Task',
  completed: true,
  dueDate: '2024-12-31T23:59:59Z',
  priority: 1,
});
```

### Delete

```typescript
// Delete single document by ID
await TasksClient.delete(documentId);

// Delete multiple documents by IDs
const idsToDelete = ['doc-id-1', 'doc-id-2', 'doc-id-3'];
await SubscriptionClient.delete(idsToDelete);
```

## Document Structure

When you read documents, AppDB returns metadata alongside your content:

```typescript
{
  "id": "1742e635-2346-42a9-a6ce-54c28880a650",          // Auto-generated
  "datastoreId": "debfdc54-92a6-413e-8e62-6d6a96329b5c", // Datastore ID
  "collectionId": "4f2fc6c9-dac8-45c1-8416-b190f0a7986a", // Collection ID
  "syncRequired": true,
  "owner": "812268184",                                   // Creator user ID
  "createdBy": "812268184",
  "createdOn": "2025-10-30T21:37:57.335Z",
  "updatedOn": "2025-10-30T21:37:57.335Z",
  "updatedBy": "812268184",
  "content": {                                            // Your data
    "title": "My Task",
    "completed": false,
    "dueDate": "2024-12-31T23:59:59Z",
    "priority": 1
  }
}
```

**Key fields:**
- `id` - Use this to update or delete specific documents
- `owner` - The user ID who created the document (used by `limitToOwner` filters)
- `createdOn` / `updatedOn` - Timestamps for sorting
- `content` - Your actual data, nested inside this object
- Query filters must prefix field names with `content.` (e.g., `'content.UID'`)

## Query Operators

### Comparison

```typescript
// Equals
{ 'content.status': { $eq: 'active' } }

// Not equal
{ 'content.status': { $ne: 'archived' } }

// Greater than
{ 'content.priority': { $gt: 2 } }

// Greater than or equal
{ 'content.priority': { $gte: 3 } }

// Less than
{ 'content.priority': { $lt: 5 } }

// Less than or equal
{ 'content.priority': { $lte: 4 } }

// In array
{ 'content.status': { $in: ['active', 'pending'] } }

// Not in array
{ 'content.status': { $nin: ['archived', 'deleted'] } }
```

### Logical

```typescript
// AND (implicit - multiple fields)
{
  'content.completed': { $eq: false },
  'content.priority': { $gte: 3 },
}

// OR
{
  $or: [
    { 'content.priority': { $eq: 5 } },
    { 'content.dueDate': { $lt: '2024-12-31' } }
  ]
}
```

### Element

```typescript
// Field exists
{ 'content.dueDate': { $exists: true } }

// Field doesn't exist
{ 'content.notes': { $exists: false } }
```

## Common Patterns

### Audit Log

**Manifest:**
```json
{
  "collections": [
    {
      "name": "EXM_Audit_Log",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "entryId", "type": "STRING" },
          { "name": "UID", "type": "STRING" },
          { "name": "field", "type": "STRING" },
          { "name": "value", "type": "STRING" }
        ]
      },
      "defaultPermission": ["READ", "READ_CONTENT", "CREATE_CONTENT"]
    }
  ]
}
```

**Service:**
```typescript
import { AppDBClient, AppDBDocument } from '@domoinc/toolkit';

interface LogEntryData {
  entryId: string;
  UID: string;
  field: string;
  value: string;
}

const AuditLogClient = new AppDBClient.DocumentsClient<LogEntryData>('EXM_Audit_Log');

const createAuditLogs = async (logs: LogEntryData[]) =>
  await AuditLogClient.create(logs);

const loadChangeLog = async (uid: string) => {
  const queryParams = { 'content.UID': { $eq: uid } };
  const options = { orderby: ['createdOn descending'] };
  return (await AuditLogClient.get(queryParams, options)).data;
};
```

### Comments System

**Manifest:**
```json
{
  "collections": [
    {
      "name": "EXM_Comments",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "UID", "type": "STRING" },
          { "name": "userEmail", "type": "STRING" },
          { "name": "userName", "type": "STRING" },
          { "name": "body", "type": "STRING" },
          { "name": "attachment", "type": "STRING" },
          { "name": "systemGenerated", "type": "STRING" }
        ]
      },
      "defaultPermission": ["READ", "READ_CONTENT", "CREATE_CONTENT"]
    }
  ]
}
```

**Service:**
```typescript
import { AppDBClient } from '@domoinc/toolkit';

interface Comment {
  UID: string;
  userEmail: string;
  userName: string;
  body: string;
  attachment?: string;
  systemGenerated?: string;
}

const CommentsClient = new AppDBClient.DocumentsClient<Comment>('EXM_Comments');

const loadComments = async (uid: string): Promise<Comment[]> => {
  const queryParams = { 'content.UID': { $eq: uid } };
  return extractAppDbData<Comment>(await CommentsClient.get(queryParams));
};

const addComment = async (comment: Comment) =>
  extractAppDbData<Comment>(await CommentsClient.create(comment))[0];

const bulkAddComments = async (comments: Comment[]) => {
  await CommentsClient.create(comments);
};
```

### Subscriptions

**Manifest:**
```json
{
  "collections": [
    {
      "name": "EXM_Subscriptions",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "UID", "type": "STRING" },
          { "name": "userEmail", "type": "STRING" }
        ]
      },
      "defaultPermission": ["READ", "READ_CONTENT", "CREATE_CONTENT", "DELETE_CONTENT"]
    }
  ]
}
```

**Service:**
```typescript
import { AppDBClient } from '@domoinc/toolkit';

interface SubscriptionData {
  UID: string;
  userEmail: string;
}

const SubscriptionClient = new AppDBClient.DocumentsClient<SubscriptionData>('EXM_Subscriptions');

const loadSubscriptions = async (uidList: string[], userEmail: string) => {
  const queryParams = {
    'content.UID': { $in: uidList },
    'content.userEmail': { $eq: userEmail },
  };
  return extractAppDbData<SubscriptionData>(await SubscriptionClient.get(queryParams));
};

const createSubscriptions = async (uids: string[], userEmail: string) => {
  const docs = uids.map(uid => ({ UID: uid, userEmail }));
  await SubscriptionClient.create(docs);
};

const deleteSubscriptions = async (ids: string[]) => {
  await SubscriptionClient.delete(ids);
};
```

### File Metadata with Owner Filter

**Manifest:**
```json
{
  "collections": [
    {
      "name": "EXM_Files_Details",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "fileId", "type": "STRING" },
          { "name": "name", "type": "STRING" },
          { "name": "UID", "type": "STRING" },
          { "name": "uploadedBy", "type": "STRING" }
        ]
      },
      "defaultPermission": [
        "READ", "READ_CONTENT", "CREATE_CONTENT", "UPDATE_CONTENT", "DELETE_CONTENT"
      ],
      "filters": [
        {
          "name": "File_Deletion_Filter",
          "applyOn": ["DELETE", "UPDATE"],
          "applyTo": [],
          "applyToAll": true,
          "limitToOwner": true,
          "query": {}
        }
      ]
    }
  ]
}
```

**Service:**
```typescript
import { AppDBClient } from '@domoinc/toolkit';
import domo from 'ryuu.js';

interface FileDetails {
  fileId: string;
  name: string;
  UID: string;
  uploadedBy: string;
}

const FilesClient = new AppDBClient.DocumentsClient<FileDetails>('EXM_Files_Details');

const uploadFile = async (file: File, UID: string, uploadedBy: string) => {
  // Upload to Domo Files
  const formData = new FormData();
  formData.append('file', file);
  const url = `/domo/data-files/v1?name=${encodeURIComponent(file.name)}&public=false`;
  const response = await domo.post(url, formData, { contentType: 'multipart' });

  // Save metadata to AppDB
  return extractAppDbData<FileDetails>(
    await FilesClient.create({
      fileId: response.dataFileId.toString(),
      name: file.name,
      UID,
      uploadedBy,
    })
  )[0];
};

const fetchFilesByUID = async (uid: string): Promise<FileDetails[]> => {
  const queryParams = { 'content.UID': { $eq: uid } };
  return extractAppDbData<FileDetails>(await FilesClient.get(queryParams));
};

const deleteFile = async (documentId: string) => {
  await FilesClient.delete(documentId);
};
```

## Best Practices

1. **Use Typed Clients** - Always create `AppDBClient.DocumentsClient<T>` for type safety
2. **Extract Helper** - Use `extractAppDbData` to simplify working with document responses
3. **Schema Planning** - Design schemas carefully; migrations are difficult
4. **Query Prefix** - Always use `content.` prefix when querying fields (e.g., `'content.UID'`)
5. **Permissions** - Start restrictive, grant more as needed
6. **Sync Enabled** - Set `syncEnabled: true` to sync data to Domo datasets
7. **Validation** - Validate data in app before saving
8. **Batch Operations** - Pass arrays to `.create()` for multiple documents
9. **Error Handling** - Always handle permission errors gracefully
10. **Pagination** - Use `limit` option for large collections
11. **Cleanup** - Delete obsolete documents periodically
12. **Document Size** - Keep documents under 100KB when possible

## Troubleshooting

**Permission Denied:**
- Check `defaultPermission` in manifest
- Verify filter rules (`limitToOwner`, `applyTo`, `applyToAll`)
- Ensure user is authenticated
- Ensure `proxyId` is set in manifest (required for AppDB)

**Document Not Found:**
- Verify document ID
- Check if document was deleted
- Ensure user has READ permission

**Schema Mismatch:**
- Redeploy app after manifest changes
- Verify field names match schema
- Check data types are correct

**Sync Issues:**
- Ensure `syncEnabled: true`
- Wait a few minutes for sync to complete
- Check Domo dataset for synced data

**AppDB Not Working At All:**
- Ensure `proxyId` exists in manifest.json
- Copy from build/manifest.json after first publish
