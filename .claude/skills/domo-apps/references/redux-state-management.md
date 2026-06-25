# Redux State Management Guide

Real-world patterns for Redux Toolkit state management in Domo Apps.

## Installation

```bash
yarn add @reduxjs/toolkit react-redux
```

## Store Configuration

### Store Setup (reducers/index.ts)

```typescript
import {
  Action,
  configureStore,
  createListenerMiddleware,
  ThunkAction,
  TypedStartListening,
} from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';

import AppReducer from './app/reducer';
import ConfigReducer from './config/reducer';
import TableReducer from './table/reducer';
// Import other reducers...

// Create listener middleware for side effects
const listenerMiddlewareInstance = createListenerMiddleware({});

export const store = configureStore({
  reducer: {
    App: AppReducer,
    Config: ConfigReducer,
    Table: TableReducer,
    // Add more reducers here
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore specific paths/actions that contain non-serializable data
        ignoredPaths: ['App.clientChannel'],
        ignoredActions: ['SET_CLIENT_CHANNEL'],
      },
    }).prepend(listenerMiddlewareInstance.middleware),
  // Add custom middleware with .concat() if needed
});

// Export typed versions
export type RootState = ReturnType<typeof store.getState>;
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  Action<string>
>;
export type AppDispatch = typeof store.dispatch;

// Typed hooks - use these instead of plain useDispatch/useSelector
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// Typed listener for side effects
export type AppStartListening = TypedStartListening<RootState, AppDispatch>;
export const startAppListening =
  listenerMiddlewareInstance.startListening as AppStartListening;
```

### Provider Setup (index.tsx)

```typescript
import React from 'react';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import { store } from './reducers';
import App from './App';

ReactDOM.render(
  <Provider store={store}>
    <App />
  </Provider>,
  document.getElementById('root')
);
```

## Reducer Pattern

### Folder Structure

```
src/reducers/
├── index.ts              # Store configuration
├── app/
│   ├── reducer.ts        # Reducer logic
│   ├── actions.ts        # Action creators
│   └── selectors.ts      # State selectors
├── table/
│   ├── reducer.ts
│   ├── actions.ts
│   └── selectors.ts
└── config/
    ├── reducer.ts
    ├── actions.ts
    └── selectors.ts
```

### Reducer (reducer.ts)

```typescript
import { createReducer } from '@reduxjs/toolkit';
import { Identity } from '@domoinc/toolkit';
import {
  loadUserInfo,
  loadDataSchemas,
  setWorkItemType,
  init,
} from './actions';

interface AppState {
  identity?: Identity;
  userRole: string;
  workItemType: string;
  entryDataSourceId?: string;
  entryDataSchema?: string[];
  loading: {
    init: number;
    userInfo: number;
    dataSchema: number;
  };
}

const initialState: AppState = {
  userRole: 'UNKNOWN',
  workItemType: 'ALL',
  loading: {
    init: 0,
    userInfo: 0,
    dataSchema: 0,
  },
};

const AppReducer = createReducer(initialState, (builder) => {
  // Sync action
  builder.addCase(setWorkItemType, (state, { payload }) => {
    state.workItemType = payload;
  });

  // Async action - init
  builder.addCase(init.pending, (state) => {
    state.loading.init += 1;
  });
  builder.addCase(init.fulfilled, (state) => {
    state.loading.init -= 1;
  });
  builder.addCase(init.rejected, (state) => {
    state.loading.init -= 1;
  });

  // Async action - loadUserInfo
  builder.addCase(loadUserInfo.pending, (state) => {
    state.loading.userInfo += 1;
  });
  builder.addCase(loadUserInfo.fulfilled, (state, { payload }) => {
    if (payload === undefined) return;
    state.identity = payload.identity;
    state.userRole = payload.role;
    state.loading.userInfo -= 1;
  });
  builder.addCase(loadUserInfo.rejected, (state) => {
    state.loading.userInfo -= 1;
  });

  // Async action - loadDataSchemas
  builder.addCase(loadDataSchemas.pending, (state) => {
    state.loading.dataSchema += 1;
  });
  builder.addCase(loadDataSchemas.fulfilled, (state, { payload }) => {
    state.entryDataSourceId = payload.entryData.id;
    state.entryDataSchema = payload.entryData.columns.map(col => col.name);
    state.loading.dataSchema -= 1;
  });
  builder.addCase(loadDataSchemas.rejected, (state) => {
    state.loading.dataSchema -= 1;
  });

  // Default case
  builder.addDefaultCase((state) => state);
});

export default AppReducer;
```

## Actions

### Sync Actions (actions.ts)

```typescript
import { createAction } from '@reduxjs/toolkit';

// Simple action with payload
export const setWorkItemType = createAction<string>('SET_WORK_ITEM_TYPE');

// Action with complex payload
export const setAresColumns = createAction<GridColumn[]>('SET_ARES_COLUMNS');

// Action without payload
export const clearFilters = createAction('CLEAR_FILTERS');
```

### Async Actions (Thunks)

```typescript
import { createAsyncThunk } from '@reduxjs/toolkit';
import { AppService } from 'services/app';
import { StorageService } from 'services/storage';
import { RootState } from 'reducers';

// Simple async thunk
export const loadUserInfo = createAsyncThunk(
  'LOAD_USER_INFO',
  AppService.loadUserInfo
);

// Async thunk with parameters
export const loadDataSchemas = createAsyncThunk(
  'LOAD_DATA_SCHEMAS',
  async () => {
    const entryData = await AppService.loadDatasetSchema('EntryData');
    return { entryData };
  }
);

// Async thunk with state access and dispatch
export const init = createAsyncThunk<
  void,
  { itemType: string | null; uIDs: string[] },
  { state: RootState; rejectValue: string }
>('INIT', async ({ itemType, uIDs }, { dispatch, getState }) => {
  try {
    // Run multiple async operations in parallel
    await Promise.all([
      dispatch(loadDataSchemas()),
      dispatch(loadUserInfo()),
      dispatch(loadFields()),
    ]);

    // Access state
    const { workItemType } = getState().App;

    // Conditional dispatch based on params
    if (itemType !== null && uIDs.length === 1) {
      dispatch(loadWorkItemDetails({ UID: uIDs[0], workItemType: itemType }));
    }

    // Sequential dispatches
    dispatch(loadCollectionIds());
    dispatch(loadTabs());
    dispatch(loadSegments());
  } catch (e) {
    console.warn(e);
  }
});

// Async thunk with rejectValue
export const checkLatestVersion = createAsyncThunk<
  number,
  { datasourceId: string; lastUpdatedDate?: number },
  { state: RootState; rejectValue: string }
>(
  'CHECK_LATEST_VERSION',
  async ({ datasourceId, lastUpdatedDate }, { dispatch, rejectWithValue }) => {
    const newVersion = await AppService.checkLatestVersion(datasourceId);

    if (newVersion === undefined) {
      return rejectWithValue('Failed to check version');
    }

    if (lastUpdatedDate && newVersion > lastUpdatedDate) {
      dispatch(refreshPageData());
    }

    return newVersion;
  }
);
```

## Selectors

### Basic Selectors (selectors.ts)

```typescript
import { RootState } from 'reducers';

// Simple selector
export const selectWorkItemType = (state: RootState) => state.App.workItemType;

// Selector with transformation
export const selectIsLoading = (state: RootState) =>
  Object.values(state.App.loading).some(count => count > 0);

// Selector accessing multiple state slices
export const selectUserEmail = (state: RootState) =>
  state.App.identity?.email;

// Complex selector
export const selectDataSchemaColumns = (state: RootState) =>
  state.App.entryDataSchema ?? [];
```

### Memoized Selectors (with Reselect)

```typescript
import { createSelector } from '@reduxjs/toolkit';
import { RootState } from 'reducers';

// Input selectors
const selectItems = (state: RootState) => state.Table.items;
const selectFilters = (state: RootState) => state.Table.filters;

// Memoized selector - only recalculates when inputs change
export const selectFilteredItems = createSelector(
  [selectItems, selectFilters],
  (items, filters) => {
    if (filters.length === 0) return items;

    return items.filter(item =>
      filters.every(filter => item[filter.column] === filter.value)
    );
  }
);

// Selector with parameters
export const makeSelectItemById = () =>
  createSelector(
    [selectItems, (state: RootState, id: string) => id],
    (items, id) => items.find(item => item.id === id)
  );
```

## Using Redux in Components

### Typed Hooks

```typescript
import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from 'reducers';
import { loadUserInfo, setWorkItemType } from 'reducers/app/actions';
import { selectWorkItemType, selectIsLoading } from 'reducers/app/selectors';

export const MyComponent: React.FC = () => {
  // Use typed hooks
  const dispatch = useAppDispatch();
  const workItemType = useAppSelector(selectWorkItemType);
  const isLoading = useAppSelector(selectIsLoading);

  // Dispatch on mount
  useEffect(() => {
    dispatch(loadUserInfo());
  }, [dispatch]);

  // Dispatch with payload
  const handleTypeChange = (newType: string) => {
    dispatch(setWorkItemType(newType));
  };

  // Dispatch async thunk
  const handleRefresh = async () => {
    await dispatch(loadDataSchemas()).unwrap();
    // .unwrap() allows you to handle promise resolution
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Work Item Type: {workItemType}</h1>
      <button onClick={() => handleTypeChange('INVOICE')}>
        Set to Invoice
      </button>
      <button onClick={handleRefresh}>Refresh</button>
    </div>
  );
};
```

### Multiple Selectors

```typescript
import { useAppSelector } from 'reducers';

export const Dashboard: React.FC = () => {
  const {
    workItemType,
    userRole,
    identity,
    isLoading,
  } = useAppSelector(state => ({
    workItemType: state.App.workItemType,
    userRole: state.App.userRole,
    identity: state.App.identity,
    isLoading: Object.values(state.App.loading).some(count => count > 0),
  }));

  return (
    <div>
      <p>User: {identity?.email}</p>
      <p>Role: {userRole}</p>
      <p>Type: {workItemType}</p>
    </div>
  );
};
```

## Service Integration

### Service Layer (services/app.ts)

```typescript
import Query from '@domoinc/query';
import { IdentityClient, UserClient } from '@domoinc/toolkit';

export const AppService = {
  async loadUserInfo() {
    const identity = (await IdentityClient.get(undefined, true)).data;
    const user = (await UserClient.getUser(identity.userId)).data;

    const url = '/domo/roles/v1/authorities/me';
    const res = await fetch(url);
    const grants = await res.json();

    const hasEditPermission = grants?.includes('edit-dataset');
    const role = user?.role?.toLowerCase() === 'admin' ? 'ADMIN' : 'USER';

    return { identity, role, hasEditPermission };
  },

  async loadDatasetSchema(datasetName: string) {
    const url = `/data/v2/${datasetName}/schema?indexedSchema=false`;
    const res = await fetch(url);
    const data = await res.json();
    return {
      id: data.dataSource.id,
      columns: data.schemaContract.schema.columns,
    };
  },

  async loadDataSourceRegistry() {
    const SCHEMA = ['WorkItemType', 'DataSetId'] as const;
    const response = await new Query()
      .select(SCHEMA)
      .fetch('DataSourceRegistry');

    return response.reduce(
      (registry, row) => ({
        ...registry,
        [row.WorkItemType]: row.DataSetId,
      }),
      {} as Record<string, string>
    );
  },
};
```

## Advanced Patterns

### Loading States Pattern

Use increment/decrement counters for tracking multiple concurrent operations:

```typescript
interface State {
  loading: {
    users: number;
    data: number;
    config: number;
  };
}

const initialState: State = {
  loading: {
    users: 0,
    data: 0,
    config: 0,
  },
};

// In reducer
builder.addCase(loadUsers.pending, (state) => {
  state.loading.users += 1; // Increment
});
builder.addCase(loadUsers.fulfilled, (state) => {
  state.loading.users -= 1; // Decrement
});
builder.addCase(loadUsers.rejected, (state) => {
  state.loading.users -= 1; // Always decrement
});

// Selector to check if ANY operation is loading
export const selectIsLoading = (state: RootState) =>
  Object.values(state.App.loading).some(count => count > 0);
```

### Listener Middleware (Side Effects)

```typescript
import { startAppListening } from 'reducers';
import { setWorkItemType } from 'reducers/app/actions';
import { refreshPageData } from 'reducers/table/actions';

// Listen for action and trigger side effect
startAppListening({
  actionCreator: setWorkItemType,
  effect: async (action, listenerApi) => {
    // Cancel any in-progress instances
    listenerApi.cancelActiveListeners();

    // Wait for debounce
    await listenerApi.delay(300);

    // Dispatch another action
    listenerApi.dispatch(refreshPageData());
  },
});
```

### Cross-Reducer Actions

Handle actions from other reducers:

```typescript
// In table/reducer.ts
import { setWorkItemType } from '../app/actions';

const TableReducer = createReducer(initialState, (builder) => {
  // Handle action from App reducer
  builder.addCase(setWorkItemType, (state, { payload }) => {
    // Clear table data when work item type changes
    state.items = [];
    state.selectedIds = [];
  });
});
```

### Optimistic Updates

```typescript
export const updateTask = createAsyncThunk(
  'tasks/update',
  async ({ id, updates }: { id: string; updates: Partial<Task> }, { rejectWithValue }) => {
    try {
      await TaskService.update(id, updates);
      return { id, updates };
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

// In reducer
builder.addCase(updateTask.pending, (state, { meta }) => {
  // Optimistically update UI
  const task = state.items.find(t => t.id === meta.arg.id);
  if (task) {
    Object.assign(task, meta.arg.updates);
  }
});
builder.addCase(updateTask.rejected, (state, { meta }) => {
  // Revert on failure - would need to store original values
  // Better: refetch data
  dispatch(fetchTasks());
});
```

## Best Practices

1. **Use Typed Hooks** - Always use `useAppDispatch` and `useAppSelector` instead of plain hooks
2. **Colocate by Feature** - Group reducer, actions, and selectors by feature domain
3. **Loading Counters** - Use increment/decrement pattern for concurrent operations
4. **Selectors for Derived State** - Create selectors for computed values, use `createSelector` for expensive computations
5. **Services for Business Logic** - Keep reducers pure, put API calls and business logic in services
6. **Thunks for Async** - Use `createAsyncThunk` for all async operations
7. **Don't Duplicate State** - Prefer selectors to derived state fields
8. **Normalize Complex State** - Use normalized structures for relational data
9. **Handle All Cases** - Always handle pending/fulfilled/rejected for async thunks
10. **Use TypeScript** - Leverage TypeScript for type safety throughout Redux

## Common Patterns

### Fetch-on-Mount Pattern

```typescript
const MyComponent: React.FC = () => {
  const dispatch = useAppDispatch();
  const data = useAppSelector(selectData);

  useEffect(() => {
    dispatch(fetchData());
  }, [dispatch]);

  return <div>{/* render data */}</div>;
};
```

### Form Submission Pattern

```typescript
const handleSubmit = async (formData: FormData) => {
  try {
    await dispatch(createItem(formData)).unwrap();
    // Success - reset form, show toast, etc.
    toast.success('Item created successfully');
    resetForm();
  } catch (error) {
    // Error - show error message
    toast.error(`Failed to create item: ${error}`);
  }
};
```

### Conditional Dispatch Pattern

```typescript
const handleAction = () => {
  const currentType = useAppSelector(selectWorkItemType);

  if (currentType === 'INVOICE') {
    dispatch(loadInvoiceData());
  } else {
    dispatch(loadGeneralData());
  }
};
```
