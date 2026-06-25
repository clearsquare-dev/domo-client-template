# Dataset Best Practices

Real-world patterns for working with Domo datasets efficiently and safely.

## Dataset Constants Pattern

### Define Aliases (constants/datasets.ts)

```typescript
// Dataset aliases - map to manifest.json mapping aliases
export const DATASET_ALIASES = {
  EntryData: 'EntryData',
  DetailTabs: 'DetailTabs',
  CoreFields: 'CoreFields',
  Owners: 'Owners',
  EmailTemplates: 'EmailTemplates',
  DomoWorkflow: 'DomoWorkflow',
  DataSourceRegistry: 'DataSourceRegistry',
} as const;

// Use as const for type safety
type DatasetAlias = typeof DATASET_ALIASES[keyof typeof DATASET_ALIASES];
```

### Define Schemas

```typescript
// Define expected columns for each dataset
export const DETAIL_TABS_SCHEMA = [
  'WorkItemType',
  'TabName',
  'Order',
  'Placement',
] as const;

export const CORE_FIELDS_SCHEMA = [
  'WorkItemType',
  'GridMapping',
  'FieldName',
  'FieldLabel',
  'SegmentName',
  'GridOrder',
  'DetailOrder',
  'DataType',
  'Bulk',
] as const;

export const OWNERS_SCHEMA = [
  'Name',
  'Email',
  'Team',
] as const;

export const DOMO_WORKFLOW_SCHEMA = [
  'WorkflowType',
  'OperationType',
  'WorkItemTypes',
  'Button',
  'TriggerColumn',
  'TriggerValue',
  'OwnerStart',
  'HourDelay',
  'Tooltip',
  'WorkflowId',
  'WorkflowVersion',
] as const;
```

**Why this pattern?**
- Single source of truth for dataset and column names
- Type safety with `as const`
- Easy refactoring if dataset names change
- Auto-completion in IDE

## Querying Datasets

### Using Query Class with Schema

```typescript
import Query from '@domoinc/query';
import { DATASET_ALIASES, CORE_FIELDS_SCHEMA } from 'constants/datasets';

// Type-safe query
const fields = await new Query()
  .select(CORE_FIELDS_SCHEMA)
  .fetch<Record<typeof CORE_FIELDS_SCHEMA[number], string>>(
    DATASET_ALIASES.CoreFields
  );

// Transform results
const fieldMap = fields.reduce((acc, row) => ({
  ...acc,
  [row.FieldName]: row.FieldLabel,
}), {} as Record<string, string>);
```

### Using SqlClient with Dynamic Queries

```typescript
import { SqlClient } from '@domoinc/toolkit';
import { DATASET_ALIASES } from 'constants/datasets';

const query = `
  SELECT "WorkItemType", "FieldName", "FieldLabel", "DataType"
  FROM table
  WHERE "WorkItemType" = 'INVOICE'
  ORDER BY "GridOrder" ASC
`;

const { data: result } = await new SqlClient().get(
  DATASET_ALIASES.CoreFields,
  query
);

// Parse SQL response
const rows = parseSqlResult(result);
```

## SQL Query Building

### Input Sanitization (CRITICAL)

```typescript
// Always sanitize user input to prevent SQL injection
export const sanitizeInput = (userInput: string) =>
  userInput
    .replace(/'/g, "''")        // Escape single quotes
    .replace(/\\/g, '\\\\')     // Escape backslashes
    .replace(/"/g, '\\"');      // Escape double quotes

// Usage
const searchTerm = sanitizeInput(userInput);
const query = `SELECT * FROM table WHERE "Name" LIKE '%${searchTerm}%'`;
```

### Building WHERE Clauses

```typescript
import { FilterOperator } from 'models/enums/filterOperator';

interface ColumnFilter {
  column: string;
  operator: FilterOperator;
  values: string[];
  dataType?: 'STRING' | 'NUMBER' | 'DATE';
}

export const buildWhereClause = (
  columns: string[],
  filters: ColumnFilter[],
  searchParams?: { column: string; value: string; }
): string => {
  const filterClauses = filters.map(filter => getFilterClause(filter));

  let whereClause = '';
  if (filterClauses.length > 0) {
    whereClause = `WHERE ${filterClauses.join(' AND ')}`;
  }

  if (searchParams) {
    const searchClause = buildSearchClause(columns, searchParams.value);
    if (whereClause) {
      whereClause += ` AND (${searchClause})`;
    } else {
      whereClause = `WHERE (${searchClause})`;
    }
  }

  return whereClause;
};
```

### Filter Operators

```typescript
export const getFilterClause = (filter: ColumnFilter): string => {
  const values = filter.values.map(v => v.replace(/'/g, "''"));
  const singleValue = values[0];
  const isDate = filter.dataType === 'DATE';

  switch (filter.operator) {
    case FilterOperator.In:
      const inValues = values.map(v => `'${v.toUpperCase()}'`).join(',');
      let clause = `UPPER("${filter.column}") IN (${inValues})`;

      // Handle NULL values
      if (values.includes('')) {
        clause = `(${clause} OR "${filter.column}" IS NULL)`;
      }
      return clause;

    case FilterOperator.NotIn:
      const notInValues = values.map(v => `'${v.toUpperCase()}'`).join(',');
      let notClause = `UPPER("${filter.column}") NOT IN (${notInValues})`;

      // Exclude NULL values
      if (values.includes('')) {
        notClause = `${notClause} AND "${filter.column}" IS NOT NULL`;
      }
      return notClause;

    case FilterOperator.Equals:
      if (isDate) {
        // For dates, use LIKE to match date portion only
        const dateOnly = singleValue.split('T')[0];
        return `"${filter.column}" LIKE '%${dateOnly}%'`;
      }
      return `UPPER("${filter.column}") = '${singleValue.toUpperCase()}'`;

    case FilterOperator.NotEquals:
      if (isDate) {
        const dateOnly = singleValue.split('T')[0];
        return `"${filter.column}" NOT LIKE '%${dateOnly}%'`;
      }
      return `UPPER("${filter.column}") != '${singleValue.toUpperCase()}'`;

    case FilterOperator.GreaterThan:
      return `"${filter.column}" > '${singleValue}'`;

    case FilterOperator.GreaterThanEqualsTo:
      return `"${filter.column}" >= '${singleValue}'`;

    case FilterOperator.LessThan:
      return `"${filter.column}" < '${singleValue}'`;

    case FilterOperator.LessThanEqualsTo:
      return `"${filter.column}" <= '${singleValue}'`;

    case FilterOperator.Between:
      return `("${filter.column}" >= '${values[0]}' AND "${filter.column}" <= '${values[1]}')`;

    default:
      return '';
  }
};
```

### Search Clause Building

```typescript
export const buildSearchClause = (
  columns: string[],
  searchStr: string,
  terms?: string[]
): string => {
  const sanitized = sanitizeInput(searchStr).trim();

  if (!sanitized) return '';

  if (!terms || terms.length <= 1) {
    // Single term search across all columns
    return columns
      .map(col => `"${col}" LIKE '%${sanitized}%'`)
      .join(' OR ');
  } else {
    // Multiple terms search
    return columns
      .map(col =>
        terms
          .map(term => `"${col}" LIKE '%${sanitizeInput(term)}%'`)
          .join(' OR ')
      )
      .join(' OR ');
  }
};
```

### ORDER BY Clause

```typescript
interface ColumnSort {
  name: string;
  direction: 'ASC' | 'DESC';
}

export const buildOrderByClause = (sorts: ColumnSort[]): string => {
  if (sorts.length === 0) return '';

  const orderClauses = sorts.map(
    sort => `"${sort.name}" ${sort.direction}`
  );

  return `ORDER BY ${orderClauses.join(', ')}`;
};

// Usage
const orderBy = buildOrderByClause([
  { name: 'Priority', direction: 'DESC' },
  { name: 'CreatedDate', direction: 'ASC' },
]);
// Result: ORDER BY "Priority" DESC, "CreatedDate" ASC
```

## Pagination Pattern

```typescript
interface PageDataInput {
  datasourceId: string;
  columns: string[];
  page: number;
  pageSize: number;
  sorts: ColumnSort[];
  filters: ColumnFilter[];
  searchParams?: SearchParams;
}

const loadPageData = async ({
  datasourceId,
  columns,
  page,
  pageSize,
  sorts,
  filters,
  searchParams,
}: PageDataInput) => {
  // Build query clauses
  const columnSelect = columns.map(col => `"${col}"`).join(',');
  const whereClause = buildWhereClause(columns, filters, searchParams);
  const orderByClause = buildOrderByClause(sorts);

  // Data query with pagination
  const dataQuery = `
    SELECT ${columnSelect}
    FROM table
    ${whereClause}
    ${orderByClause}
    LIMIT ${pageSize}
    OFFSET ${(page - 1) * pageSize}
  `;

  // Count query for total records
  const countQuery = `
    SELECT COUNT("UID") AS COUNT
    FROM table
    ${whereClause}
  `;

  // Execute both queries in parallel
  const [dataResult, countResult] = await Promise.all([
    executeSQL(datasourceId, dataQuery),
    executeSQL(datasourceId, countQuery),
  ]);

  const data = parseSqlResult(dataResult);
  const count = parseInt(parseSqlResult(countResult)[0].COUNT, 10);

  return { data, count };
};
```

## SQL Response Parsing

### Parse SQL Response

```typescript
import { SqlResponse } from '@domoinc/toolkit';

export const parseSqlResult = (response: SqlResponse): Record<string, any>[] => {
  return response.rows.map(row =>
    row.reduce((obj, value, index) => {
      obj[response.columns[index]] = value;
      return obj;
    }, {} as Record<string, any>)
  );
};

// Usage
const result = await executeSQL(datasetId, query);
const rows = parseSqlResult(result);

// rows is now: [{ column1: value1, column2: value2 }, ...]
```

### Type-Safe Parsing

```typescript
interface WorkItem {
  UID: string;
  Status: string;
  Owner: string;
  CreatedDate: string;
}

const parseWorkItems = (response: SqlResponse): WorkItem[] => {
  return parseSqlResult(response) as WorkItem[];
};
```

## Data Transformation Patterns

### Client-Side Sorting

```typescript
import moment from 'moment';

export const sortDataClientSide = <T extends Record<string, any>>(
  data: T[],
  sorts: ColumnSort[]
): T[] => {
  const parseValue = (value: any) => {
    // Try to parse as date
    if (moment(value, 'YYYY-MM-DDTHH:mm:ss', true).isValid()) {
      return new Date(value);
    }
    // Try to parse as number
    if (!isNaN(parseFloat(value)) && isFinite(parseFloat(value))) {
      return parseFloat(value);
    }
    return value;
  };

  return [...data].sort((a, b) => {
    for (const sort of sorts) {
      const valA = parseValue(a[sort.name]);
      const valB = parseValue(b[sort.name]);

      if (valA < valB) {
        return sort.direction === 'ASC' ? -1 : 1;
      }
      if (valA > valB) {
        return sort.direction === 'ASC' ? 1 : -1;
      }
    }
    return 0;
  });
};
```

### Data Aggregation

```typescript
// Group by and aggregate
const groupByWorkItemType = (data: WorkItem[]) => {
  return data.reduce((acc, item) => {
    const type = item.WorkItemType;
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(item);
    return acc;
  }, {} as Record<string, WorkItem[]>);
};

// Create lookup map
const createOwnerMap = (owners: Owner[]) => {
  return owners.reduce((map, owner) => {
    map[owner.Email] = owner.Name;
    return map;
  }, {} as Record<string, string>);
};
```

## Schema Management

### Load and Cache Schema

```typescript
const SCHEMA_CACHE = new Map<string, DatasetSchema>();

interface DatasetSchema {
  id: string;
  columns: Array<{ name: string; type: string }>;
}

export const loadDatasetSchema = async (
  datasetName: string
): Promise<DatasetSchema> => {
  // Check cache first
  if (SCHEMA_CACHE.has(datasetName)) {
    return SCHEMA_CACHE.get(datasetName)!;
  }

  // Fetch schema
  const url = `/data/v2/${datasetName}/schema?indexedSchema=false`;
  const res = await fetch(url);
  const data = await res.json();

  const schema = {
    id: data.dataSource.id,
    columns: data.schemaContract.schema.columns,
  };

  // Cache it
  SCHEMA_CACHE.set(datasetName, schema);

  return schema;
};
```

### Validate Required Columns

```typescript
const validateColumns = (
  schema: DatasetSchema,
  requiredColumns: string[]
): { valid: boolean; missing: string[] } => {
  const schemaColumns = schema.columns.map(col => col.name);
  const missing = requiredColumns.filter(col => !schemaColumns.includes(col));

  return {
    valid: missing.length === 0,
    missing,
  };
};

// Usage
const schema = await loadDatasetSchema('EntryData');
const validation = validateColumns(schema, ['UID', 'Status', 'Owner']);

if (!validation.valid) {
  throw new Error(`Missing columns: ${validation.missing.join(', ')}`);
}
```

## Error Handling

### Query Error Handling

```typescript
const safeQuery = async <T>(
  datasetAlias: string,
  query: string
): Promise<T[] | null> => {
  try {
    const result = await executeSQL(datasetAlias, query);
    return parseSqlResult(result) as T[];
  } catch (error) {
    console.error(`Query failed for ${datasetAlias}:`, error);

    // Log query for debugging (sanitize sensitive data first)
    console.error('Failed query:', query);

    // Return null or empty array based on your needs
    return null;
  }
};
```

### Retry Pattern for Dataset Queries

```typescript
const queryWithRetry = async <T>(
  datasetAlias: string,
  query: string,
  maxRetries: number = 3,
  delayMs: number = 1000
): Promise<T[]> => {
  let lastError: Error;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const result = await executeSQL(datasetAlias, query);
      return parseSqlResult(result) as T[];
    } catch (error) {
      lastError = error as Error;

      if (attempt < maxRetries - 1) {
        const delay = delayMs * Math.pow(2, attempt); // Exponential backoff
        console.warn(`Query attempt ${attempt + 1} failed, retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError!;
};
```

## Performance Optimization

### Limit Initial Queries

```typescript
// Bad: Loading all data upfront
const allData = await loadAllRecords(); // Could be 100k+ rows

// Good: Load only what's needed
const pageData = await loadPageData({
  page: 1,
  pageSize: 50,
  // ... other params
});
```

### Use Indexes Wisely

```typescript
// Bad: Filtering on non-indexed column
const query = `
  SELECT * FROM table
  WHERE "Description" LIKE '%keyword%'
`;

// Good: Filter on indexed columns (UID, dates, etc.)
const query = `
  SELECT * FROM table
  WHERE "UID" IN ('uid1', 'uid2', 'uid3')
`;
```

### Parallel Queries

```typescript
// Execute independent queries in parallel
const [owners, workflows, templates] = await Promise.all([
  loadOwners(),
  loadWorkflows(),
  loadEmailTemplates(),
]);

// Sequential queries (when order matters)
const registry = await loadDataSourceRegistry();
const entryDataId = registry['INVOICE'];
const entryData = await loadEntryData(entryDataId);
```

## Best Practices Summary

1. **Constants** - Always define dataset aliases and schemas as constants
2. **Sanitization** - ALWAYS sanitize user input before using in SQL queries
3. **Type Safety** - Use `as const` and TypeScript types for schemas
4. **Query Building** - Use utility functions to build WHERE/ORDER BY clauses
5. **Pagination** - Never load all data; always paginate large datasets
6. **Error Handling** - Implement retry logic and proper error logging
7. **Caching** - Cache schemas and static data to reduce API calls
8. **Parallel Execution** - Use Promise.all() for independent queries
9. **SQL Response Parsing** - Always parse SQL responses into typed objects
10. **Column Quoting** - Always quote column names with double quotes: `"ColumnName"`

## Common Pitfalls

### ❌ SQL Injection Risk
```typescript
// NEVER do this
const query = `SELECT * FROM table WHERE "Name" = '${userInput}'`;
```

### ✅ Always Sanitize
```typescript
// Always sanitize
const sanitized = sanitizeInput(userInput);
const query = `SELECT * FROM table WHERE "Name" = '${sanitized}'`;
```

### ❌ Magic Strings
```typescript
// Hard to maintain
const data = await new Query().select(['col1', 'col2']).fetch('MyDataset');
```

### ✅ Use Constants
```typescript
// Easy to refactor
const data = await new Query()
  .select(MY_DATASET_SCHEMA)
  .fetch(DATASET_ALIASES.MyDataset);
```

### ❌ Loading Too Much Data
```typescript
// Loads everything into memory
const allRows = await executeSQL(datasetId, 'SELECT * FROM table');
```

### ✅ Paginate
```typescript
// Load only what's needed
const page = await loadPageData({ page: 1, pageSize: 50, ... });
```
