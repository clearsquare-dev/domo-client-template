# App with AppDB Collections

A complete example of a Domo Custom App using multiple AppDB collections for state persistence, user preferences, audit logging, and file metadata. Builds on the simple-app.md patterns with more complex collection interactions.

## Use Case

A project tracker app where:
- Projects and tasks are stored in AppDB collections
- Users can set personal preferences (theme, default view)
- All changes are tracked in an audit log
- Files can be attached to projects

## Project Structure

```
project-tracker/
├── public/
│   ├── manifest.json
│   └── thumbnail.png
├── src/
│   ├── components/
│   │   ├── ProjectList.tsx
│   │   ├── ProjectDetail.tsx
│   │   ├── TaskBoard.tsx
│   │   ├── AuditLog.tsx
│   │   ├── FileAttachments.tsx
│   │   └── UserPreferences.tsx
│   ├── services/
│   │   ├── projectService.ts
│   │   ├── taskService.ts
│   │   ├── auditService.ts
│   │   ├── fileService.ts
│   │   └── preferencesService.ts
│   ├── reducers/
│   │   ├── index.ts
│   │   ├── projects/
│   │   ├── tasks/
│   │   └── preferences/
│   ├── types/
│   │   └── index.ts
│   └── index.tsx
└── package.json
```

## manifest.json

```json
{
  "name": "Project Tracker",
  "version": "1.0.0",
  "size": { "width": 8, "height": 6 },
  "fullpage": true,
  "collections": [
    {
      "name": "Projects",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "name", "type": "STRING" },
          { "name": "description", "type": "STRING" },
          { "name": "status", "type": "STRING" },
          { "name": "priority", "type": "STRING" },
          { "name": "startDate", "type": "STRING" },
          { "name": "dueDate", "type": "STRING" },
          { "name": "ownerEmail", "type": "STRING" },
          { "name": "tags", "type": "STRING" }
        ]
      },
      "defaultPermission": [
        "READ", "READ_CONTENT", "CREATE_CONTENT", "UPDATE_CONTENT", "DELETE_CONTENT"
      ]
    },
    {
      "name": "Tasks",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "projectId", "type": "STRING" },
          { "name": "title", "type": "STRING" },
          { "name": "description", "type": "STRING" },
          { "name": "status", "type": "STRING" },
          { "name": "assigneeEmail", "type": "STRING" },
          { "name": "dueDate", "type": "STRING" },
          { "name": "priority", "type": "STRING" },
          { "name": "order", "type": "STRING" }
        ]
      },
      "defaultPermission": [
        "READ", "READ_CONTENT", "CREATE_CONTENT", "UPDATE_CONTENT", "DELETE_CONTENT"
      ]
    },
    {
      "name": "AuditLog",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "entityType", "type": "STRING" },
          { "name": "entityId", "type": "STRING" },
          { "name": "action", "type": "STRING" },
          { "name": "field", "type": "STRING" },
          { "name": "oldValue", "type": "STRING" },
          { "name": "newValue", "type": "STRING" },
          { "name": "userEmail", "type": "STRING" }
        ]
      },
      "defaultPermission": [
        "READ", "READ_CONTENT", "CREATE_CONTENT"
      ]
    },
    {
      "name": "FileAttachments",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "entityType", "type": "STRING" },
          { "name": "entityId", "type": "STRING" },
          { "name": "fileId", "type": "STRING" },
          { "name": "fileName", "type": "STRING" },
          { "name": "uploadedBy", "type": "STRING" }
        ]
      },
      "defaultPermission": [
        "READ", "READ_CONTENT", "CREATE_CONTENT", "DELETE_CONTENT"
      ],
      "filters": [
        {
          "name": "OwnerDeleteOnly",
          "applyOn": ["DELETE"],
          "applyTo": [],
          "applyToAll": true,
          "limitToOwner": true,
          "query": {}
        }
      ]
    },
    {
      "name": "UserPreferences",
      "syncEnabled": false,
      "schema": {
        "columns": [
          { "name": "userEmail", "type": "STRING" },
          { "name": "theme", "type": "STRING" },
          { "name": "defaultView", "type": "STRING" },
          { "name": "notificationsEnabled", "type": "STRING" }
        ]
      },
      "defaultPermission": [
        "CREATE_CONTENT"
      ],
      "filters": [
        {
          "name": "UserOwnData",
          "applyOn": ["READ", "UPDATE", "DELETE"],
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

### Collection Design Notes

| Collection | Sync | Permission Pattern | Why |
|-----------|------|-------------------|-----|
| Projects | Yes | Full access for all | Collaborative editing |
| Tasks | Yes | Full access for all | Team task management |
| AuditLog | Yes | Read + Create only | Append-only, no edits or deletes |
| FileAttachments | Yes | Owner-delete filter | Anyone can upload, only owner can delete |
| UserPreferences | No | Owner-only via filter | Private user settings, no need to sync |

## types/index.ts

```typescript
// --- Data models (without AppDB metadata) ---

export interface ProjectData {
  name: string;
  description: string;
  status: 'planning' | 'active' | 'on-hold' | 'complete';
  priority: 'low' | 'medium' | 'high' | 'critical';
  startDate: string;
  dueDate: string;
  ownerEmail: string;
  tags: string; // JSON-stringified array
}

export interface Project extends ProjectData {
  id: string;
}

export interface TaskData {
  projectId: string;
  title: string;
  description: string;
  status: 'backlog' | 'todo' | 'in-progress' | 'review' | 'done';
  assigneeEmail: string;
  dueDate: string;
  priority: 'low' | 'medium' | 'high';
  order: string; // Stored as string, parsed as number
}

export interface Task extends TaskData {
  id: string;
}

export interface AuditEntry {
  entityType: 'project' | 'task';
  entityId: string;
  action: 'create' | 'update' | 'delete' | 'status-change';
  field: string;
  oldValue: string;
  newValue: string;
  userEmail: string;
}

export interface FileAttachment {
  id: string;
  entityType: 'project' | 'task';
  entityId: string;
  fileId: string;
  fileName: string;
  uploadedBy: string;
}

export interface UserPreference {
  id: string;
  userEmail: string;
  theme: 'light' | 'dark';
  defaultView: 'board' | 'list' | 'timeline';
  notificationsEnabled: string; // 'true' or 'false'
}
```

## services/projectService.ts

```typescript
import { AppDBClient, AppDBDocument } from '@domoinc/toolkit';
import { ProjectData, Project } from '../types';

const COLLECTION = 'Projects';
const ProjectsClient = new AppDBClient.DocumentsClient<ProjectData>(COLLECTION);

// Helper to extract content with ID from AppDB response
const extractDocs = <T>(response: { data: AppDBDocument<T>[] }): (T & { id: string })[] =>
  response.data.map(doc => ({
    id: doc.id,
    ...doc.content,
  }));

export const projectService = {
  async getAll(): Promise<Project[]> {
    return extractDocs<ProjectData>(await ProjectsClient.get({}, {}));
  },

  async getById(id: string): Promise<Project | null> {
    const response = await ProjectsClient.get({}, {});
    const doc = response.data.find(d => d.id === id);
    if (!doc) return null;
    return { id: doc.id, ...doc.content };
  },

  async getByStatus(status: string): Promise<Project[]> {
    const queryParams = { 'content.status': { $eq: status } };
    return extractDocs<ProjectData>(await ProjectsClient.get(queryParams, {}));
  },

  async create(data: ProjectData): Promise<Project> {
    return extractDocs<ProjectData>(await ProjectsClient.create(data))[0];
  },

  async update(id: string, updates: Partial<ProjectData>): Promise<void> {
    // Fetch current to merge
    const response = await ProjectsClient.get({}, {});
    const doc = response.data.find(d => d.id === id);
    if (!doc) throw new Error('Project not found');

    await ProjectsClient.update(id, {
      ...doc.content,
      ...updates,
    });
  },

  async delete(id: string): Promise<void> {
    await ProjectsClient.delete(id);
  },

  async search(query: string): Promise<Project[]> {
    // AppDB doesn't support text search, so fetch all and filter client-side
    const all = await this.getAll();
    const lower = query.toLowerCase();
    return all.filter(
      p =>
        p.name.toLowerCase().includes(lower) ||
        p.description.toLowerCase().includes(lower)
    );
  },
};
```

## services/auditService.ts

```typescript
import { AppDBClient, AppDBDocument } from '@domoinc/toolkit';
import { AuditEntry } from '../types';

const COLLECTION = 'AuditLog';
const AuditClient = new AppDBClient.DocumentsClient<AuditEntry>(COLLECTION);

const extractDocs = <T>(response: { data: AppDBDocument<T>[] }): (T & { id: string; createdOn: string; owner: string })[] =>
  response.data.map(doc => ({
    id: doc.id,
    createdOn: doc.createdOn,
    owner: doc.owner,
    ...doc.content,
  }));

export const auditService = {
  async getByEntity(entityType: string, entityId: string) {
    const queryParams = {
      'content.entityType': { $eq: entityType },
      'content.entityId': { $eq: entityId },
    };
    const options = { orderby: ['createdOn descending'] };
    return extractDocs<AuditEntry>(
      await AuditClient.get(queryParams, options)
    );
  },

  async logChange(
    entityType: 'project' | 'task',
    entityId: string,
    action: string,
    field: string,
    oldValue: string,
    newValue: string,
    userEmail: string
  ): Promise<void> {
    await AuditClient.create({
      entityType,
      entityId,
      action,
      field,
      oldValue,
      newValue,
      userEmail,
    });
  },

  async logBulkChanges(entries: AuditEntry[]): Promise<void> {
    if (entries.length > 0) {
      await AuditClient.create(entries);
    }
  },
};
```

## services/fileService.ts

```typescript
import { AppDBClient, AppDBDocument } from '@domoinc/toolkit';
import domo from 'ryuu.js';
import { FileAttachment } from '../types';

const COLLECTION = 'FileAttachments';

interface FileAttachmentData {
  entityType: string;
  entityId: string;
  fileId: string;
  fileName: string;
  uploadedBy: string;
}

const FilesClient = new AppDBClient.DocumentsClient<FileAttachmentData>(COLLECTION);

const extractDocs = <T>(response: { data: AppDBDocument<T>[] }): (T & { id: string })[] =>
  response.data.map(doc => ({ id: doc.id, ...doc.content }));

export const fileService = {
  async getByEntity(entityType: string, entityId: string): Promise<FileAttachment[]> {
    const queryParams = {
      'content.entityType': { $eq: entityType },
      'content.entityId': { $eq: entityId },
    };
    return extractDocs<FileAttachmentData>(
      await FilesClient.get(queryParams, {})
    );
  },

  async upload(
    file: File,
    entityType: string,
    entityId: string,
    uploadedBy: string
  ): Promise<FileAttachment> {
    // Upload file to Domo Files API
    const formData = new FormData();
    formData.append('file', file);
    const url = `/domo/data-files/v1?name=${encodeURIComponent(file.name)}&public=false`;
    const response = await domo.post(
      url,
      formData,
      { contentType: 'multipart' }
    );
    const dataFileId = response.dataFileId;

    // Save metadata to AppDB
    return extractDocs<FileAttachmentData>(
      await FilesClient.create({
        entityType,
        entityId,
        fileId: dataFileId.toString(),
        fileName: file.name,
        uploadedBy,
      })
    )[0];
  },

  async delete(documentId: string): Promise<void> {
    await FilesClient.delete(documentId);
  },
};
```

## services/preferencesService.ts

```typescript
import { AppDBClient, AppDBDocument } from '@domoinc/toolkit';
import { UserPreference } from '../types';

const COLLECTION = 'UserPreferences';

interface PreferenceData {
  userEmail: string;
  theme: string;
  defaultView: string;
  notificationsEnabled: string;
}

const PrefsClient = new AppDBClient.DocumentsClient<PreferenceData>(COLLECTION);

const DEFAULTS: Omit<UserPreference, 'id' | 'userEmail'> = {
  theme: 'light',
  defaultView: 'board',
  notificationsEnabled: 'true',
};

export const preferencesService = {
  async get(userEmail: string): Promise<UserPreference> {
    // With limitToOwner filter, this only returns the current user's docs
    const response = await PrefsClient.get({}, {});
    const doc = response.data.find(d => d.content.userEmail === userEmail);

    if (!doc) {
      // Create default preferences
      const created = await PrefsClient.create({
        userEmail,
        ...DEFAULTS,
      });
      const newDoc = created.data[0];
      return { id: newDoc.id, ...newDoc.content } as UserPreference;
    }

    return { id: doc.id, ...doc.content } as UserPreference;
  },

  async update(id: string, updates: Partial<PreferenceData>): Promise<void> {
    const response = await PrefsClient.get({}, {});
    const doc = response.data.find(d => d.id === id);
    if (!doc) throw new Error('Preferences not found');

    await PrefsClient.update(id, {
      ...doc.content,
      ...updates,
    });
  },
};
```

## Updating with Audit Trail

A key pattern is combining updates with audit logging:

```typescript
// services/projectService.ts (enhanced update)
import { auditService } from './auditService';

async updateWithAudit(
  id: string,
  updates: Partial<ProjectData>,
  userEmail: string
): Promise<void> {
  // Get current values for diff
  const current = await this.getById(id);
  if (!current) throw new Error('Project not found');

  // Build audit entries for changed fields
  const auditEntries = Object.entries(updates)
    .filter(([key, value]) => current[key as keyof ProjectData] !== value)
    .map(([key, value]) => ({
      entityType: 'project' as const,
      entityId: id,
      action: key === 'status' ? 'status-change' as const : 'update' as const,
      field: key,
      oldValue: String(current[key as keyof ProjectData] ?? ''),
      newValue: String(value ?? ''),
      userEmail,
    }));

  // Perform update
  await this.update(id, updates);

  // Log changes
  await auditService.logBulkChanges(auditEntries);
}
```

## Tags Pattern (JSON in STRING column)

Since AppDB only supports `STRING` columns, store arrays as JSON strings:

```typescript
// Storing tags
const tags = ['frontend', 'urgent', 'sprint-12'];
await projectService.create({
  name: 'Dashboard Redesign',
  tags: JSON.stringify(tags),
  // ...other fields
});

// Reading tags
const project = await projectService.getById(id);
const tags: string[] = JSON.parse(project.tags || '[]');

// Filtering by tag (client-side, since AppDB can't query JSON)
const allProjects = await projectService.getAll();
const tagged = allProjects.filter(p => {
  const projectTags: string[] = JSON.parse(p.tags || '[]');
  return projectTags.includes('urgent');
});
```

## Key Patterns

1. **Typed Clients** — Create `AppDBClient.DocumentsClient<T>` for every collection
2. **Extract Helper** — Reusable function to map `AppDBDocument<T>` to `T & { id }`
3. **Merge on Update** — Fetch current document, spread updates, then save (AppDB replaces entire content)
4. **Audit Trail** — Diff old vs. new values, bulk-create audit entries
5. **Owner Filter** — Use `limitToOwner: true` for user-private data (preferences) and delete-protection (files)
6. **Append-Only Collections** — AuditLog has no UPDATE or DELETE permissions
7. **JSON in STRING** — Store complex types as JSON strings, parse on read
8. **Client-Side Search** — AppDB doesn't support text search; fetch and filter in-memory
9. **Sync Control** — Enable `syncEnabled` for collections you want queryable as Domo datasets; disable for ephemeral data
10. **Default Values** — Create defaults on first access (preferences pattern)

## MCP Development Workflow

Use MCP tools to set up and verify collections during development:

```
# Create collections before writing app code
appdb_collection_create(name="Projects", schema={...})
appdb_collection_create(name="Tasks", schema={...})
appdb_collection_create(name="AuditLog", schema={...})

# Seed test data
appdb_bulk_insert(collection_id, [
  { name: "Dashboard Redesign", status: "active", priority: "high", ... },
  { name: "API Migration", status: "planning", priority: "medium", ... }
])

# Verify documents
appdb_document_list(collection_id)

# Test query patterns
appdb_document_list(collection_id, query={ "content.status": { "$eq": "active" } })
```

This catches schema and permission issues before you write any React code.
