# Testing Guide

Patterns for testing Domo Custom Apps with Jest and React Testing Library.

## Setup

### Dependencies (included with da new template)

```json
{
  "devDependencies": {
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.0.0",
    "@types/jest": "^29.0.0"
  }
}
```

### Run Tests

```bash
yarn test                    # Watch mode
yarn test --watchAll=false   # Single run
yarn test --coverage         # With coverage report

# CI mode
yarn test -- --watchAll=false --ci --runInBand --forceExit --passWithNoTests
```

## Mocking Domo APIs

### Mock @domoinc/toolkit

Create `src/__mocks__/@domoinc/toolkit.ts`:

```typescript
export const mockGet = jest.fn();
export const mockCreate = jest.fn();
export const mockUpdate = jest.fn();
export const mockDelete = jest.fn();

export const AppDBClient = {
  DocumentsClient: jest.fn().mockImplementation(() => ({
    get: mockGet,
    create: mockCreate,
    update: mockUpdate,
    delete: mockDelete,
  })),
};

export const IdentityClient = {
  get: jest.fn().mockResolvedValue({
    data: {
      userId: 123,
      email: 'test@example.com',
      displayName: 'Test User',
    },
  }),
};

export const UserClient = {
  getUser: jest.fn().mockResolvedValue({
    data: {
      id: 123,
      displayName: 'Test User',
      email: 'test@example.com',
      role: 'Admin',
    },
  }),
};

export const SqlClient = jest.fn().mockImplementation(() => ({
  get: jest.fn().mockResolvedValue({
    data: { columns: [], rows: [] },
  }),
}));

export const DataFormatTypes = {
  json: 'application/json',
};

export type AppDBDocument<T> = {
  id: string;
  owner: string;
  createdOn: string;
  updatedOn: string;
  content: T;
};
```

### Mock @domoinc/query

Create `src/__mocks__/@domoinc/query.ts`:

```typescript
const mockFetch = jest.fn().mockResolvedValue([]);

const Query = jest.fn().mockImplementation(() => ({
  select: jest.fn().mockReturnThis(),
  fetch: mockFetch,
}));

export default Query;
export { mockFetch };
```

### Mock ryuu.js

Create `src/__mocks__/ryuu.js.ts`:

```typescript
const domo = {
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
};

export default domo;
```

### Mock fetch (for direct API calls)

```typescript
// In test file or setupTests.ts
global.fetch = jest.fn();

const mockFetch = (data: any, status = 200) => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: jest.fn().mockResolvedValueOnce(data),
  });
};

// Usage
mockFetch({ columns: ['UID', 'Status'], rows: [['uid-1', 'Active']] });
```

## Testing Services

### Testing AppDB Service

```typescript
import { mockGet, mockCreate, mockDelete } from '@domoinc/toolkit';

// Reset mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
});

describe('StorageService', () => {
  describe('loadChangeLog', () => {
    it('should query audit log by UID', async () => {
      const mockLogs = {
        data: [
          {
            id: 'doc-1',
            owner: '123',
            createdOn: '2025-01-01T00:00:00Z',
            content: {
              entryId: '1',
              UID: 'uid-1',
              field: 'status',
              value: 'completed',
            },
          },
        ],
      };

      mockGet.mockResolvedValueOnce(mockLogs);

      const { StorageService } = await import('services/storage');
      const result = await StorageService.loadChangeLog('uid-1', []);

      expect(mockGet).toHaveBeenCalledWith(
        { 'content.UID': { $eq: 'uid-1' } },
        { orderby: ['createdOn descending'] }
      );
      expect(result.logs).toHaveLength(1);
      expect(result.logs[0].field).toBe('status');
    });
  });

  describe('createAuditLogs', () => {
    it('should create multiple log entries', async () => {
      const logs = [
        { entryId: '1', UID: 'uid-1', field: 'status', value: 'new' },
        { entryId: '2', UID: 'uid-1', field: 'priority', value: 'high' },
      ];

      mockCreate.mockResolvedValueOnce({ data: [] });

      const { StorageService } = await import('services/storage');
      await StorageService.createAuditLogs(logs);

      expect(mockCreate).toHaveBeenCalledWith(logs);
    });
  });

  describe('deleteSubscriptions', () => {
    it('should delete by document IDs', async () => {
      mockDelete.mockResolvedValueOnce({});

      const { StorageService } = await import('services/storage');
      await StorageService.deleteSubscriptions(['doc-1', 'doc-2']);

      expect(mockDelete).toHaveBeenCalledWith(['doc-1', 'doc-2']);
    });
  });
});
```

### Testing Query Service

```typescript
import Query, { mockFetch } from '@domoinc/query';

describe('ConfigService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should load workflow configuration', async () => {
    mockFetch.mockResolvedValueOnce([
      {
        WorkflowType: 'Approval',
        OperationType: 'Submit',
        WorkItemTypes: 'INVOICE,PAYMENT',
        Button: 'Approve',
        WorkflowId: 'wf-123',
        WorkflowVersion: '1',
      },
    ]);

    const { ConfigService } = await import('services/config');
    const workflows = await ConfigService.loadDomoWorkflows();

    expect(workflows).toHaveLength(1);
    expect(workflows[0].workflowType).toBe('Approval');
    expect(workflows[0].workItemTypes).toEqual(['INVOICE', 'PAYMENT']);
  });
});
```

### Testing SQL Service

```typescript
describe('TableService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should load paginated data', async () => {
    const mockResponse = {
      columns: ['UID', 'Status', 'Owner'],
      rows: [
        ['uid-1', 'Active', 'john@example.com'],
        ['uid-2', 'Pending', 'jane@example.com'],
      ],
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce(mockResponse),
    });

    // Count query response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce({
        columns: ['COUNT'],
        rows: [['50']],
      }),
    });

    const { TableService } = await import('services/table');
    const result = await TableService.loadPageData({
      datasourceId: 'ds-123',
      columns: ['UID', 'Status', 'Owner'],
      page: 1,
      pageSize: 25,
      sortColumns: [],
      columnFilters: [],
    });

    expect(result.data).toHaveLength(2);
    expect(result.count).toBe(50);
    expect(result.data[0].UID).toBe('uid-1');
  });
});
```

## Testing Redux

### Testing Actions (Thunks)

```typescript
import { configureStore } from '@reduxjs/toolkit';
import AppReducer from 'reducers/app/reducer';
import { loadUserInfo, init } from 'reducers/app/actions';
import { IdentityClient, UserClient } from '@domoinc/toolkit';

const createTestStore = () =>
  configureStore({
    reducer: { App: AppReducer },
  });

describe('App Actions', () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    store = createTestStore();
    jest.clearAllMocks();
  });

  it('should load user info and update state', async () => {
    (IdentityClient.get as jest.Mock).mockResolvedValueOnce({
      data: { userId: 123, email: 'test@example.com' },
    });
    (UserClient.getUser as jest.Mock).mockResolvedValueOnce({
      data: { id: 123, displayName: 'Test', role: 'Admin' },
    });
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce(['edit-dataset']),
    });

    await store.dispatch(loadUserInfo());

    const state = store.getState().App;
    expect(state.identity?.email).toBe('test@example.com');
    expect(state.userRole).toBe('ADMIN');
    expect(state.loading.userInfo).toBe(0);
  });

  it('should track loading state during init', async () => {
    // Verify loading increments
    const initPromise = store.dispatch(init({
      categoryType: null,
      itemType: null,
      uIDs: [],
      shareLinkMode: 'Standard',
    }));

    expect(store.getState().App.loading.init).toBe(1);

    await initPromise;

    expect(store.getState().App.loading.init).toBe(0);
  });
});
```

### Testing Reducers

```typescript
import AppReducer from 'reducers/app/reducer';
import { setWorkItemType } from 'reducers/app/actions';

describe('AppReducer', () => {
  const initialState = {
    userRole: 'UNKNOWN',
    workItemType: 'ALL',
    loading: { init: 0, userInfo: 0, dataSchema: 0 },
  };

  it('should return initial state', () => {
    const state = AppReducer(undefined, { type: 'UNKNOWN' });
    expect(state.workItemType).toBe('ALL');
  });

  it('should handle setWorkItemType', () => {
    const state = AppReducer(
      initialState as any,
      setWorkItemType('INVOICE')
    );
    expect(state.workItemType).toBe('INVOICE');
  });
});
```

### Testing Selectors

```typescript
import { selectWorkItemType, selectIsLoading } from 'reducers/app/selectors';

describe('App Selectors', () => {
  const mockState = {
    App: {
      workItemType: 'INVOICE',
      loading: { init: 0, userInfo: 1, dataSchema: 0 },
    },
  } as any;

  it('should select work item type', () => {
    expect(selectWorkItemType(mockState)).toBe('INVOICE');
  });

  it('should detect loading state', () => {
    expect(selectIsLoading(mockState)).toBe(true);
  });

  it('should return false when nothing is loading', () => {
    const idleState = {
      App: { loading: { init: 0, userInfo: 0, dataSchema: 0 } },
    } as any;
    expect(selectIsLoading(idleState)).toBe(false);
  });
});
```

## Testing Components

### Render Helper with Redux

```typescript
// src/test-utils.tsx
import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import AppReducer from 'reducers/app/reducer';
import TasksReducer from 'reducers/tasks/reducer';

interface RenderWithStoreOptions extends Omit<RenderOptions, 'wrapper'> {
  preloadedState?: any;
}

export const renderWithStore = (
  ui: React.ReactElement,
  { preloadedState, ...renderOptions }: RenderWithStoreOptions = {}
) => {
  const store = configureStore({
    reducer: {
      App: AppReducer,
      Tasks: TasksReducer,
    },
    preloadedState,
  });

  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <Provider store={store}>{children}</Provider>
  );

  return {
    store,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
};
```

### Testing a Component

```typescript
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithStore } from 'test-utils';
import { TaskList } from 'components/TaskList';

describe('TaskList', () => {
  it('should render tasks from state', () => {
    renderWithStore(<TaskList />, {
      preloadedState: {
        Tasks: {
          items: [
            { id: '1', title: 'Task One', completed: false, dueDate: '2025-12-31' },
            { id: '2', title: 'Task Two', completed: true, dueDate: '2025-06-15' },
          ],
          loading: { fetch: 0 },
          error: null,
        },
      },
    });

    expect(screen.getByText('Task One')).toBeInTheDocument();
    expect(screen.getByText('Task Two')).toBeInTheDocument();
  });

  it('should show loading spinner', () => {
    renderWithStore(<TaskList />, {
      preloadedState: {
        Tasks: {
          items: [],
          loading: { fetch: 1 },
          error: null,
        },
      },
    });

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should show error message', () => {
    renderWithStore(<TaskList />, {
      preloadedState: {
        Tasks: {
          items: [],
          loading: { fetch: 0 },
          error: 'Failed to fetch tasks',
        },
      },
    });

    expect(screen.getByText('Failed to fetch tasks')).toBeInTheDocument();
  });

  it('should toggle task on checkbox click', async () => {
    const user = userEvent.setup();

    const { store } = renderWithStore(<TaskList />, {
      preloadedState: {
        Tasks: {
          items: [
            { id: '1', title: 'Task One', completed: false, dueDate: '2025-12-31' },
          ],
          loading: { fetch: 0 },
          error: null,
        },
      },
    });

    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);

    // Verify the toggle action was dispatched
    const actions = store.getState();
    // Check state or dispatched actions as needed
  });
});
```

### Testing Forms

```typescript
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithStore } from 'test-utils';
import { TaskForm } from 'components/TaskForm';

describe('TaskForm', () => {
  it('should submit form with title and date', async () => {
    const user = userEvent.setup();

    renderWithStore(<TaskForm />, {
      preloadedState: {
        Tasks: { items: [], loading: { fetch: 0 }, error: null },
      },
    });

    await user.type(screen.getByLabelText('Task Title'), 'New Task');
    await user.type(screen.getByLabelText('Due Date'), '2025-12-31');
    await user.click(screen.getByRole('button', { name: /add task/i }));

    // Verify form was cleared after submission
    await waitFor(() => {
      expect(screen.getByLabelText('Task Title')).toHaveValue('');
    });
  });

  it('should not submit empty form', async () => {
    const user = userEvent.setup();

    renderWithStore(<TaskForm />, {
      preloadedState: {
        Tasks: { items: [], loading: { fetch: 0 }, error: null },
      },
    });

    await user.click(screen.getByRole('button', { name: /add task/i }));

    // Form should still have empty values (not submitted)
    expect(screen.getByLabelText('Task Title')).toHaveValue('');
  });
});
```

## Testing Utilities

### Testing Query Utils

```typescript
import { sanitizeInput, buildWhereClause, buildOrderByClause } from 'utils/queryUtils';

describe('queryUtils', () => {
  describe('sanitizeInput', () => {
    it('should escape single quotes', () => {
      expect(sanitizeInput("O'Brien")).toBe("O''Brien");
    });

    it('should escape backslashes', () => {
      expect(sanitizeInput('path\\to')).toBe('path\\\\to');
    });

    it('should escape double quotes', () => {
      expect(sanitizeInput('say "hello"')).toBe('say \\"hello\\"');
    });

    it('should handle multiple special characters', () => {
      expect(sanitizeInput("it's a \"test\" with \\")).toBe(
        "it''s a \\\"test\\\" with \\\\"
      );
    });
  });

  describe('buildWhereClause', () => {
    it('should return empty string with no filters', () => {
      expect(buildWhereClause([], [])).toBe('');
    });

    it('should build IN clause', () => {
      const result = buildWhereClause([], [
        {
          column: 'Status',
          operator: 'IN',
          values: ['Active', 'Pending'],
        },
      ]);

      expect(result).toContain('UPPER("Status") IN');
      expect(result).toContain("'ACTIVE'");
      expect(result).toContain("'PENDING'");
    });
  });

  describe('buildOrderByClause', () => {
    it('should return empty string with no sorts', () => {
      expect(buildOrderByClause([])).toBe('');
    });

    it('should build order by clause', () => {
      const result = buildOrderByClause([
        { name: 'Priority', direction: 'DESC' },
        { name: 'Name', direction: 'ASC' },
      ]);

      expect(result).toBe('ORDER BY "Priority" DESC, "Name" ASC');
    });
  });
});
```

### Testing parseSqlResult

```typescript
import { parseSqlResult } from 'utils/tableUtils';

describe('parseSqlResult', () => {
  it('should convert SQL response to objects', () => {
    const response = {
      columns: ['UID', 'Status', 'Owner'],
      rows: [
        ['uid-1', 'Active', 'john@example.com'],
        ['uid-2', 'Pending', 'jane@example.com'],
      ],
    };

    const result = parseSqlResult(response);

    expect(result).toEqual([
      { UID: 'uid-1', Status: 'Active', Owner: 'john@example.com' },
      { UID: 'uid-2', Status: 'Pending', Owner: 'jane@example.com' },
    ]);
  });

  it('should handle empty results', () => {
    const response = { columns: ['UID'], rows: [] };
    expect(parseSqlResult(response)).toEqual([]);
  });
});
```

## Test File Organization

```
src/
├── __mocks__/
│   ├── @domoinc/
│   │   ├── toolkit.ts
│   │   └── query.ts
│   └── ryuu.js.ts
├── test-utils.tsx              # Render helper with Redux
├── components/
│   ├── TaskList.tsx
│   └── TaskList.test.tsx       # Component test next to component
├── services/
│   ├── storage.ts
│   └── storage.test.ts
├── reducers/
│   └── app/
│       ├── reducer.ts
│       ├── reducer.test.ts
│       ├── actions.ts
│       ├── actions.test.ts
│       └── selectors.test.ts
└── utils/
    ├── queryUtils.ts
    └── queryUtils.test.ts
```

## Best Practices

1. **Colocate Tests** - Put `.test.ts` files next to the code they test
2. **Mock at Boundaries** - Mock `@domoinc/toolkit`, `@domoinc/query`, `ryuu.js`, and `fetch`
3. **Test Behavior** - Test what components do, not implementation details
4. **Use Typed Mocks** - Keep mock return types matching real API responses
5. **Reset Between Tests** - Always `jest.clearAllMocks()` in `beforeEach`
6. **Test Redux in Isolation** - Test reducers, actions, and selectors separately
7. **Use renderWithStore** - Create a helper that wraps components with Redux Provider
8. **Test Loading States** - Verify loading spinners appear during async operations
9. **Test Error States** - Verify error messages display correctly
10. **Use userEvent** - Prefer `@testing-library/user-event` over `fireEvent` for realistic interactions
