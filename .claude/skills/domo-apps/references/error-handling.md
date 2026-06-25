# Error Handling Guide for Domo Custom Apps

## Overview

Error handling in Domo Custom Apps spans multiple layers. Each layer has a distinct responsibility:

| Layer | Responsibility |
|---|---|
| **Redux Error State** | Centralized error storage, categorized by domain |
| **Service Functions** | Catching failures, recording analytics, returning safe values |
| **Async Thunks** | Validating preconditions, rejecting with typed messages |
| **User Notifications** | Displaying toast messages via react-toastify |
| **Error Constants** | Centralized, consistent messaging |

Errors flow upward: services catch raw failures, thunks translate them into typed rejections, the Redux store categorizes and stores them, and the UI layer presents them to users.

---

## 1. Redux Error State

Use a dedicated errors reducer built with `createReducer` from Redux Toolkit. Categorize errors by domain so components can display or respond to specific failure types.

### Error State Shape

```ts
// types/errors.ts
export interface ErrorState {
  backgroundError: string | null;
  commentError: string | null;
  configError: string | null;
  dataError: string | null;
  fileError: string | null;
  savingError: string | null;
  workflowError: string | null;
}
```

### Error Reducer

```ts
// store/errors/errorsReducer.ts
import { createReducer, isRejected, AnyAction } from '@reduxjs/toolkit';
import { ErrorState } from '../../types/errors';

// Actions that map to specific error categories
import { fetchConfig } from '../config/configThunks';
import { fetchData, saveRecord } from '../data/dataThunks';
import { uploadFile } from '../files/fileThunks';
import { submitWorkflow } from '../workflow/workflowThunks';
import { addComment } from '../comments/commentThunks';

const initialState: ErrorState = {
  backgroundError: null,
  commentError: null,
  configError: null,
  dataError: null,
  fileError: null,
  savingError: null,
  workflowError: null,
};

// Map thunks to the error field they should populate
const configThunks = [fetchConfig];
const dataThunks = [fetchData];
const savingThunks = [saveRecord];
const fileThunks = [uploadFile];
const workflowThunks = [submitWorkflow];
const commentThunks = [addComment];

function isOneOf(action: AnyAction, thunks: Array<{ rejected: { type: string } }>) {
  return thunks.some((thunk) => action.type === thunk.rejected.type);
}

const errorsReducer = createReducer(initialState, (builder) => {
  // Clear specific error categories
  builder.addCase('errors/clearDataError', (state) => {
    state.dataError = null;
  });
  builder.addCase('errors/clearSavingError', (state) => {
    state.savingError = null;
  });
  builder.addCase('errors/clearConfigError', (state) => {
    state.configError = null;
  });
  builder.addCase('errors/clearFileError', (state) => {
    state.fileError = null;
  });
  builder.addCase('errors/clearWorkflowError', (state) => {
    state.workflowError = null;
  });
  builder.addCase('errors/clearCommentError', (state) => {
    state.commentError = null;
  });
  builder.addCase('errors/clearAllErrors', () => initialState);

  // Match all rejected thunks and route to the correct error field
  builder.addMatcher(isRejected, (state, action) => {
    const message = (action.payload as string) ?? action.error?.message ?? 'An unexpected error occurred';

    if (isOneOf(action, configThunks)) {
      state.configError = message;
    } else if (isOneOf(action, dataThunks)) {
      state.dataError = message;
    } else if (isOneOf(action, savingThunks)) {
      state.savingError = message;
    } else if (isOneOf(action, fileThunks)) {
      state.fileError = message;
    } else if (isOneOf(action, workflowThunks)) {
      state.workflowError = message;
    } else if (isOneOf(action, commentThunks)) {
      state.commentError = message;
    } else {
      state.backgroundError = message;
    }
  });
});

export default errorsReducer;
```

### Error Actions

```ts
// store/errors/errorActions.ts
import { createAction } from '@reduxjs/toolkit';

export const clearDataError = createAction('errors/clearDataError');
export const clearSavingError = createAction('errors/clearSavingError');
export const clearConfigError = createAction('errors/clearConfigError');
export const clearFileError = createAction('errors/clearFileError');
export const clearWorkflowError = createAction('errors/clearWorkflowError');
export const clearCommentError = createAction('errors/clearCommentError');
export const clearAllErrors = createAction('errors/clearAllErrors');
```

### Error Selectors

```ts
// store/errors/errorSelectors.ts
import { RootState } from '../store';

export const selectDataError = (state: RootState) => state.errors.dataError;
export const selectSavingError = (state: RootState) => state.errors.savingError;
export const selectConfigError = (state: RootState) => state.errors.configError;
export const selectFileError = (state: RootState) => state.errors.fileError;
export const selectWorkflowError = (state: RootState) => state.errors.workflowError;
export const selectCommentError = (state: RootState) => state.errors.commentError;
export const selectBackgroundError = (state: RootState) => state.errors.backgroundError;
export const selectHasAnyError = (state: RootState) =>
  Object.values(state.errors).some((val) => val !== null);
```

---

## 2. Service Error Handling

Service functions are the boundary between the app and external APIs (AppDB, datasets, Domo API). Every service function should:

1. Wrap the call in try/catch
2. Record the error via analytics
3. Show a user notification when appropriate
4. Return `undefined` on failure (never throw)

### Pattern: Try/Catch with Analytics and Toast

```ts
// services/DataService.ts
import domo from 'ryuu.js';
import { toast } from 'react-toastify';
import { AnalyticsService } from './AnalyticsService';
import { NOTIFICATION_MESSAGES } from '../constants/notificationMessages';

export class DataService {
  static async fetchRecords(datasetId: string): Promise<Record<string, unknown>[] | undefined> {
    try {
      const response = await domo.get(`/data/v1/${datasetId}?limit=10000`);
      return response;
    } catch (error) {
      AnalyticsService.recordError('DataService.fetchRecords', error);
      toast.error(NOTIFICATION_MESSAGES.DATA_FETCH_ERROR, { autoClose: 5000 });
      return undefined;
    }
  }

  static async updateRecord(
    datasetId: string,
    payload: Record<string, unknown>
  ): Promise<boolean> {
    try {
      await domo.put(`/data/v1/${datasetId}`, payload);
      toast.success(NOTIFICATION_MESSAGES.SAVE_SUCCESS, { autoClose: 3000 });
      return true;
    } catch (error) {
      AnalyticsService.recordError('DataService.updateRecord', error);
      toast.error(NOTIFICATION_MESSAGES.SAVE_ERROR, { autoClose: 5000 });
      return false;
    }
  }
}
```

### Pattern: AppDB Service with Error Handling

```ts
// services/AppDBService.ts
import { AppDBClient } from '@domoinc/toolkit';
import { toast } from 'react-toastify';
import { AnalyticsService } from './AnalyticsService';
import { NOTIFICATION_MESSAGES } from '../constants/notificationMessages';

const appdb = new AppDBClient();

export class AppDBService {
  static async getDocument(collectionName: string, documentId: string): Promise<unknown | undefined> {
    try {
      const result = await appdb.getDocument(collectionName, documentId);
      return result;
    } catch (error) {
      AnalyticsService.recordError('AppDBService.getDocument', error);
      return undefined;
    }
  }

  static async createDocument(
    collectionName: string,
    content: Record<string, unknown>
  ): Promise<unknown | undefined> {
    try {
      const result = await appdb.createDocument(collectionName, content);
      return result;
    } catch (error) {
      AnalyticsService.recordError('AppDBService.createDocument', error);
      toast.error(NOTIFICATION_MESSAGES.SAVE_ERROR, { autoClose: 5000 });
      return undefined;
    }
  }
}
```

### Pattern: Query Service with .catch() Chaining

```ts
// services/QueryService.ts
import Query from '@domoinc/query';
import { AnalyticsService } from './AnalyticsService';

export class QueryService {
  static fetchFilteredData(datasetAlias: string, filters: Record<string, string>) {
    const query = new Query();
    query.select(['column1', 'column2']);

    Object.entries(filters).forEach(([col, val]) => {
      query.where(col).equals(val);
    });

    return query
      .fetch(datasetAlias)
      .then((data: unknown[]) => data)
      .catch((error: unknown) => {
        AnalyticsService.recordError('QueryService.fetchFilteredData', error);
        return undefined;
      });
  }
}
```

### Analytics Service

```ts
// services/AnalyticsService.ts
import domo from 'ryuu.js';

export class AnalyticsService {
  static recordError(source: string, error: unknown): void {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[${source}]`, errorMessage);

    // Send to Domo for tracking (fire-and-forget)
    domo
      .post('/domo/datastores/v1/collections/error_logs/documents/', {
        source,
        errorMessage,
        timestamp: new Date().toISOString(),
      })
      .catch(() => {
        // Silently fail - do not recurse on analytics errors
      });
  }

  static recordEvent(eventName: string, metadata?: Record<string, unknown>): void {
    domo
      .post('/domo/datastores/v1/collections/analytics/documents/', {
        event: eventName,
        ...metadata,
        timestamp: new Date().toISOString(),
      })
      .catch(() => {});
  }
}
```

---

## 3. Async Thunk Error Handling

Async thunks are the bridge between services and the Redux store. Use `rejectWithValue` to send typed, user-friendly error messages into the errors reducer.

### Pattern: Basic Thunk with rejectWithValue

```ts
// store/data/dataThunks.ts
import { createAsyncThunk } from '@reduxjs/toolkit';
import { DataService } from '../../services/DataService';
import { AnalyticsService } from '../../services/AnalyticsService';
import { NOTIFICATION_MESSAGES } from '../../constants/notificationMessages';

export const fetchData = createAsyncThunk<
  Record<string, unknown>[],  // Return type
  string,                      // Argument type (datasetId)
  { rejectValue: string }      // rejectWithValue type
>(
  'data/fetchData',
  async (datasetId, { rejectWithValue }) => {
    const result = await DataService.fetchRecords(datasetId);

    if (!result) {
      return rejectWithValue(NOTIFICATION_MESSAGES.DATA_FETCH_ERROR);
    }

    AnalyticsService.recordEvent('data_fetched', { count: result.length });
    return result;
  }
);
```

### Pattern: Precondition Validation and Access Errors

```ts
// store/workflow/workflowThunks.ts
import { createAsyncThunk } from '@reduxjs/toolkit';
import { RootState } from '../store';
import { WorkflowService } from '../../services/WorkflowService';
import { AnalyticsService } from '../../services/AnalyticsService';
import { NOTIFICATION_MESSAGES } from '../../constants/notificationMessages';

export const submitWorkflow = createAsyncThunk<
  void,
  { recordId: string; action: string },
  { state: RootState; rejectValue: string }
>(
  'workflow/submit',
  async ({ recordId, action }, { getState, rejectWithValue }) => {
    const state = getState();
    const userRole = state.user.role;

    // Precondition: check access before making the call
    if (!userRole || !['admin', 'approver'].includes(userRole)) {
      AnalyticsService.recordEvent('workflow_access_denied', { recordId, userRole });
      return rejectWithValue(NOTIFICATION_MESSAGES.ACCESS_DENIED);
    }

    const record = state.data.records.find((r) => r.id === recordId);
    if (!record) {
      return rejectWithValue(NOTIFICATION_MESSAGES.RECORD_NOT_FOUND);
    }

    try {
      await WorkflowService.submit(recordId, action);
      AnalyticsService.recordEvent('workflow_submitted', { recordId, action });
    } catch (error) {
      AnalyticsService.recordError('submitWorkflow', error);
      return rejectWithValue(NOTIFICATION_MESSAGES.WORKFLOW_ERROR);
    }
  }
);
```

### Pattern: Differentiating Error Types

```ts
// store/config/configThunks.ts
import { createAsyncThunk } from '@reduxjs/toolkit';
import { AppDBService } from '../../services/AppDBService';
import { AnalyticsService } from '../../services/AnalyticsService';
import { NOTIFICATION_MESSAGES } from '../../constants/notificationMessages';

interface AppConfig {
  features: Record<string, boolean>;
  settings: Record<string, unknown>;
}

export const fetchConfig = createAsyncThunk<
  AppConfig,
  void,
  { rejectValue: string }
>(
  'config/fetch',
  async (_, { rejectWithValue }) => {
    try {
      const config = await AppDBService.getDocument('app_config', 'main');

      if (!config) {
        return rejectWithValue(NOTIFICATION_MESSAGES.CONFIG_LOAD_ERROR);
      }

      return config as AppConfig;
    } catch (error: unknown) {
      // Differentiate between access errors (403) and general errors
      if (error instanceof Error && error.message.includes('403')) {
        AnalyticsService.recordEvent('config_access_denied');
        return rejectWithValue(NOTIFICATION_MESSAGES.ACCESS_DENIED);
      }

      AnalyticsService.recordError('fetchConfig', error);
      return rejectWithValue(NOTIFICATION_MESSAGES.GENERAL_ERROR);
    }
  }
);
```

---

## 4. User Notifications

Use `react-toastify` for all user-facing notifications. Configure a single `ToastContainer` at the app root and call `toast.*` methods from services and components.

### Toast Container Setup

```tsx
// App.tsx
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

function App() {
  return (
    <>
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        pauseOnHover
      />
      <MainContent />
    </>
  );
}
```

### Toast Usage Patterns

```ts
import { toast } from 'react-toastify';

// Error with longer display time
toast.error('Failed to save changes. Please try again.', { autoClose: 5000 });

// Success with shorter display time
toast.success('Record saved successfully.', { autoClose: 3000 });

// Warning
toast.warn('You have unsaved changes.', { autoClose: 4000 });

// Info
toast.info('Data is being refreshed.', { autoClose: 3000 });
```

### Showing Errors from Redux State in Components

```tsx
// components/ErrorBanner.tsx
import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { toast } from 'react-toastify';
import { selectDataError } from '../store/errors/errorSelectors';
import { clearDataError } from '../store/errors/errorActions';

const ErrorBanner: React.FC = () => {
  const dispatch = useDispatch();
  const dataError = useSelector(selectDataError);

  useEffect(() => {
    if (dataError) {
      toast.error(dataError, {
        autoClose: 5000,
        onClose: () => dispatch(clearDataError()),
      });
    }
  }, [dataError, dispatch]);

  return null; // Toast handles the display
};
```

---

## 5. Error Constants

Centralize all notification messages in a constants file. This keeps messages consistent and makes them easy to update.

```ts
// constants/notificationMessages.ts
export const NOTIFICATION_MESSAGES = {
  // Data errors
  DATA_FETCH_ERROR: 'Unable to load data. Please refresh the page and try again.',
  RECORD_NOT_FOUND: 'The requested record could not be found.',

  // Save errors
  SAVE_SUCCESS: 'Changes saved successfully.',
  SAVE_ERROR: 'Failed to save changes. Please try again.',

  // Config errors
  CONFIG_LOAD_ERROR: 'Unable to load application configuration.',

  // File errors
  FILE_UPLOAD_ERROR: 'File upload failed. Please check the file and try again.',
  FILE_UPLOAD_SUCCESS: 'File uploaded successfully.',
  FILE_SIZE_ERROR: 'File exceeds the maximum allowed size.',

  // Workflow errors
  WORKFLOW_ERROR: 'Unable to complete the workflow action. Please try again.',
  WORKFLOW_SUCCESS: 'Workflow action completed successfully.',

  // Access errors
  ACCESS_DENIED: 'You do not have permission to perform this action.',

  // Comment errors
  COMMENT_ERROR: 'Unable to save comment. Please try again.',
  COMMENT_SUCCESS: 'Comment added successfully.',

  // General
  GENERAL_ERROR: 'An unexpected error occurred. Please try again.',
  NETWORK_ERROR: 'A network error occurred. Please check your connection.',
} as const;

export type NotificationMessageKey = keyof typeof NOTIFICATION_MESSAGES;
```

---

## 6. Best Practices

### Do

- **Categorize errors in the Redux store.** Use distinct fields (`dataError`, `savingError`, etc.) so the UI can respond to each independently.
- **Use `rejectWithValue` in every thunk.** This gives the errors reducer a typed, user-friendly string instead of a raw serialized error.
- **Validate preconditions before API calls.** Check user roles, required fields, and record existence in the thunk before calling a service. This avoids unnecessary network requests.
- **Record errors to analytics.** Call `AnalyticsService.recordError()` in services so you can track failure rates. Do this before returning undefined or rejecting.
- **Return `undefined` from services on failure.** Never throw from a service function. The caller (thunk) decides how to handle the absence of data.
- **Use centralized message constants.** Never hardcode notification strings in services or thunks. Import from `NOTIFICATION_MESSAGES`.
- **Clear errors when the user navigates or retries.** Dispatch `clearDataError()` (or the relevant clear action) so stale errors do not persist.
- **Keep toast durations appropriate.** Use shorter durations (3000ms) for success, longer (5000ms) for errors so users have time to read them.

### Do Not

- **Do not throw from service functions.** Return `undefined` and let the thunk handle it with `rejectWithValue`.
- **Do not show raw error messages to users.** Map errors to constants from `NOTIFICATION_MESSAGES`. Raw messages may expose internal details.
- **Do not silently swallow errors.** Always record to analytics even if you do not show a toast.
- **Do not duplicate error state.** Store errors only in the errors reducer, not in each feature slice. This prevents conflicting error states.
- **Do not forget to handle the rejected case.** If a component dispatches a thunk, it should either rely on the errors reducer or check the returned action with `.unwrap()`.

### Using `.unwrap()` for Inline Error Handling

When a component needs to respond to a thunk outcome directly (for example, closing a modal on success), use `.unwrap()`:

```tsx
const handleSave = async () => {
  try {
    await dispatch(saveRecord({ id, payload })).unwrap();
    // Success: close modal, navigate, etc.
    closeModal();
  } catch (rejectedValue) {
    // The errors reducer already has the error.
    // Only add component-specific logic here if needed.
  }
};
```

### Error Handling Checklist

When adding a new feature, verify:

1. Service function has try/catch and returns `undefined` on failure
2. Service function calls `AnalyticsService.recordError()` in the catch block
3. Thunk uses `rejectWithValue` with a message from `NOTIFICATION_MESSAGES`
4. Thunk is registered in the errors reducer under the correct category
5. Relevant clear action exists for the error category
6. Component either reads from the errors reducer or uses `.unwrap()`
7. Toast notification is shown where appropriate (service or component level, not both)
