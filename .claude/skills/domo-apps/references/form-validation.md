# Form Validation Patterns Guide

Real-world patterns for form validation in Domo Custom Apps, based on the US Bank Exception Management project.

## Overview

Validation in Domo Custom Apps is organized into three layers:

1. **Utility Layer** - Pure functions for validating individual values (email, GUID, file names, emptiness checks). These are reusable across the entire application.
2. **Component Layer** - React state-driven error tracking, inline error display with MUI components, and form submission guards that prevent invalid data from reaching the Redux layer.
3. **Redux Layer** - Pre-validation inside `createAsyncThunk` using `rejectWithValue` to catch invalid state before API calls. Also includes dirty checking and duplicate detection.

Each layer catches different classes of errors. Use all three together for robust validation.

## Validation Utilities

### Core Validators (utils/validation.ts)

```typescript
/**
 * Check if a value is empty (empty string, undefined, or null).
 */
export const isEmpty = (value: any) =>
  value === '' || value === undefined || value === null;

/**
 * Validate a GUID format.
 */
export const isGUID = (value: string) =>
  /^[a-f\d]{8}-([a-f\d]{4}-){3}[a-f\d]{12}$/i.test(value);
```

### Email Validation

```typescript
/**
 * Validate a single email address.
 */
export const validateEmail = (email: string) =>
  /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i.test(email);

/**
 * Parse a comma-separated string of emails into objects
 * with validity flags.
 */
export const parseEmails = (emails: string) =>
  emails
    .split(',')
    .map((email) => email.trim())
    .filter((value) => value.length > 0)
    .map((email) => ({ email, valid: validateEmail(email) }));

/**
 * Validate a comma-separated email string.
 * Returns true when all emails are valid.
 * When required is false, an empty string is acceptable.
 */
export const validateEmails = (emails: string, required: boolean) => {
  const parsedEmails = parseEmails(emails);
  if (parsedEmails.length === 0 && required === false) return true;
  return Object.values(parsedEmails).every(({ valid }) => valid === true);
};
```

### File Name Validation

```typescript
/**
 * Check that a file name contains only safe characters:
 * letters, numbers, dots, underscores, spaces, hyphens,
 * dollar signs, and commas.
 */
export const isValidFileName = (name: string) =>
  /[^a-zA-Z0-9._\s\-$,]/.test(name) === false;
```

### Custom Validators

Build domain-specific validators by composing the primitives:

```typescript
/**
 * Validate a UID field: must not be empty and must be a valid GUID.
 */
export const validateUID = (value: string): string | undefined => {
  if (isEmpty(value)) return 'UID is required';
  if (!isGUID(value)) return 'UID must be a valid GUID';
  return undefined;
};

/**
 * Validate a numeric range.
 */
export const validateRange = (
  value: number,
  min: number,
  max: number,
): string | undefined => {
  if (value < min || value > max)
    return `Value must be between ${min} and ${max}`;
  return undefined;
};
```

## Component-Level Validation

### Error State Pattern

Use a typed error object that mirrors the form fields. Each key holds either an error message string or `undefined` when the field is valid.

```typescript
import React, { useState } from 'react';
import { Box, Button, TextField } from '@mui/material';
import { toast } from 'react-toastify';
import { validateEmail, validateEmails, isEmpty } from 'utils/validation';

interface Email {
  to: string;
  cc: string;
  subject: string;
  body: string;
}

const initialValues: Email = {
  to: '',
  cc: '',
  subject: '',
  body: '',
};

export const SendEmail: React.FC = () => {
  const [values, setValues] = useState<Email>(initialValues);
  const [errors, setErrors] = useState<{ [k in keyof Email]?: string }>({});

  // Generic setter for a single field
  const setValue = <K extends keyof Email>(key: K, value: Email[K]) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  // Generic error setter for a single field
  const setError = <K extends keyof Email>(key: K, message?: string) =>
    setErrors((prev) => ({ ...prev, [key]: message }));

  const validate = (): boolean => {
    let isValid = true;

    // Required field: 'to'
    if (isEmpty(values.to)) {
      setError('to', 'At least one recipient is required');
      isValid = false;
    } else if (!validateEmails(values.to, true)) {
      setError('to', 'One or more email addresses are invalid');
      isValid = false;
    } else {
      setError('to', undefined);
    }

    // Optional field: 'cc'
    if (!validateEmails(values.cc, false)) {
      setError('cc', 'One or more CC addresses are invalid');
      isValid = false;
    } else {
      setError('cc', undefined);
    }

    // Required field: 'subject'
    if (isEmpty(values.subject)) {
      setError('subject', 'Subject is required');
      isValid = false;
    } else {
      setError('subject', undefined);
    }

    return isValid;
  };

  const handleSubmit = () => {
    if (!validate()) {
      toast.error('Please fix the errors before sending');
      return;
    }

    // Proceed with submission
    // dispatch(sendEmail(values));
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <TextField
        label="To"
        value={values.to}
        onChange={(e) => setValue('to', e.target.value)}
        error={errors.to !== undefined}
        helperText={errors.to}
        placeholder="comma-separated emails"
        required
      />
      <TextField
        label="CC"
        value={values.cc}
        onChange={(e) => setValue('cc', e.target.value)}
        error={errors.cc !== undefined}
        helperText={errors.cc}
        placeholder="comma-separated emails"
      />
      <TextField
        label="Subject"
        value={values.subject}
        onChange={(e) => setValue('subject', e.target.value)}
        error={errors.subject !== undefined}
        helperText={errors.subject}
        required
      />
      <TextField
        label="Body"
        value={values.body}
        onChange={(e) => setValue('body', e.target.value)}
        multiline
        rows={4}
      />
      <Button variant="contained" onClick={handleSubmit}>
        Send
      </Button>
    </Box>
  );
};
```

### Inline Error Display with InputProps

For cases where you need error indicators inside the input (e.g., an icon in the endAdornment), use the `InputProps` prop on MUI `TextField`:

```typescript
import { InputAdornment } from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

<TextField
  label="To"
  value={values.to}
  onChange={(e) => setValue('to', e.target.value)}
  error={errors.to !== undefined}
  helperText={errors.to}
  InputProps={{
    endAdornment: errors.to ? (
      <InputAdornment position="end">
        <ErrorOutlineIcon color="error" />
      </InputAdornment>
    ) : undefined,
  }}
/>
```

### Clearing Errors on Change

To clear an error as soon as the user starts editing a field, reset the error in the change handler:

```typescript
const handleChange = <K extends keyof Email>(key: K, value: Email[K]) => {
  setValue(key, value);
  if (errors[key] !== undefined) {
    setError(key, undefined);
  }
};
```

## File Upload Validation

### react-dropzone with Custom Validator

Use a custom `validator` function in `useDropzone` to reject files with invalid names before they enter state. Combine with `maxFiles` and `onDropRejected` for a complete solution.

```typescript
import React from 'react';
import { useDropzone } from 'react-dropzone';
import { Box, Typography } from '@mui/material';
import { toast } from 'react-toastify';
import { isValidFileName } from 'utils/validation';

const MAX_FILES = 5;

interface FileUploadProps {
  files: File[];
  onFilesAccepted: (files: File[]) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  files,
  onFilesAccepted,
}) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    maxFiles: MAX_FILES - files.length,

    // Custom validator runs per file
    validator: (file) => {
      if (isValidFileName(file.name) === false) {
        toast.error(
          `"${file.name}" contains invalid characters. ` +
            'Only letters, numbers, dots, underscores, hyphens, ' +
            'dollar signs, and commas are allowed.',
        );
        return {
          code: 'Invalid characters',
          message: 'File name contains invalid characters',
        };
      }
      return null; // null means valid
    },

    onDropAccepted: (acceptedFiles) => {
      // Enforce max files with splice as a safety net
      const combined = [...files, ...acceptedFiles];
      if (combined.length > MAX_FILES) {
        toast.warn(`Only ${MAX_FILES} files are allowed. Extra files removed.`);
        combined.splice(MAX_FILES);
      }
      onFilesAccepted(combined);
    },

    onDropRejected: (rejectedFiles) => {
      rejectedFiles.forEach(({ file, errors }) => {
        errors.forEach((err) => {
          if (err.code === 'too-many-files') {
            toast.error(`Maximum of ${MAX_FILES} files allowed.`);
          }
        });
      });
    },
  });

  return (
    <Box
      {...getRootProps()}
      sx={{
        border: '2px dashed',
        borderColor: isDragActive ? 'primary.main' : 'grey.400',
        borderRadius: 1,
        p: 3,
        textAlign: 'center',
        cursor: 'pointer',
      }}
    >
      <input {...getInputProps()} />
      <Typography>
        {isDragActive
          ? 'Drop files here...'
          : `Drag & drop files here, or click to select (max ${MAX_FILES})`}
      </Typography>
    </Box>
  );
};
```

### Key Points

- Return `null` from the validator when the file is valid; return an error object to reject it.
- The error object shape is `{ code: string; message: string }`.
- Use `splice` as a safety net when combining existing and newly dropped files.
- Show toast notifications for rejected files so the user understands why a file was ignored.

## Async Thunk Pre-validation

Validate required state and preconditions inside `createAsyncThunk` before making API calls. Use `rejectWithValue` to return a typed error string that reducers can handle.

### Pattern: Guard Clauses with rejectWithValue

```typescript
import { createAsyncThunk } from '@reduxjs/toolkit';
import { RootState } from 'reducers';
import { AppNotificationMessage } from 'constants/notifications';

export const submitEntry = createAsyncThunk<
  void,
  { uid: string; changes: Record<string, any> },
  { state: RootState; rejectValue: string }
>(
  'SUBMIT_ENTRY',
  async ({ uid, changes }, { getState, rejectWithValue }) => {
    const { activeWorkItem, entryDataSchema } = getState().App;
    const { currentData } = getState().Table;
    const { identity } = getState().App;

    // Guard: required config must exist
    if (activeWorkItem === undefined || entryDataSchema === undefined) {
      return rejectWithValue(AppNotificationMessage.CONFIG_MISSING);
    }

    // Guard: required data must exist
    if (currentData === undefined || identity === undefined) {
      return rejectWithValue(AppNotificationMessage.DATA_MISSING);
    }

    // All preconditions met - proceed with the operation
    await EntryService.submit({
      uid,
      changes,
      schema: entryDataSchema,
      user: identity.email,
    });
  },
);
```

### Handling Rejected Thunks in the Reducer

```typescript
import { createReducer } from '@reduxjs/toolkit';
import { toast } from 'react-toastify';
import { submitEntry } from './actions';

const EntryReducer = createReducer(initialState, (builder) => {
  builder.addCase(submitEntry.pending, (state) => {
    state.loading.submit += 1;
  });
  builder.addCase(submitEntry.fulfilled, (state) => {
    state.loading.submit -= 1;
    toast.success('Entry submitted successfully');
  });
  builder.addCase(submitEntry.rejected, (state, action) => {
    state.loading.submit -= 1;

    // action.payload is the rejectWithValue string
    if (action.payload) {
      toast.error(action.payload);
    } else {
      // Unexpected error (network failure, etc.)
      toast.error('An unexpected error occurred');
    }
  });
});
```

### Handling Rejected Thunks in Components

```typescript
const handleSubmit = async () => {
  try {
    await dispatch(submitEntry({ uid, changes })).unwrap();
    toast.success('Saved');
  } catch (errorMessage) {
    // errorMessage is the rejectWithValue string
    toast.error(errorMessage as string);
  }
};
```

### Duplicate Detection in Thunks

Check for duplicates before creating new records:

```typescript
export const createEntry = createAsyncThunk<
  void,
  { uid: string; data: Record<string, any> },
  { state: RootState; rejectValue: string }
>(
  'CREATE_ENTRY',
  async ({ uid, data }, { getState, rejectWithValue }) => {
    const existingItems = getState().Table.items;
    const duplicate = existingItems.find((item) => item.UID === uid);

    if (duplicate) {
      return rejectWithValue(`An entry with UID "${uid}" already exists`);
    }

    await EntryService.create({ uid, data });
  },
);
```

## Dirty Checking / Change Detection

### JSON Comparison Pattern

Use `JSON.stringify` comparison to detect whether form values have changed from their initial state. This is useful for enabling/disabling save buttons and preventing unnecessary API calls.

```typescript
import React, { useMemo, useState } from 'react';
import { Box, Button, TextField } from '@mui/material';

interface FormValues {
  name: string;
  description: string;
  category: string;
}

interface EditFormProps {
  initialValues: FormValues;
  onSave: (values: FormValues) => void;
}

export const EditForm: React.FC<EditFormProps> = ({
  initialValues,
  onSave,
}) => {
  const [editedValues, setEditedValues] = useState<FormValues>(initialValues);

  const isDirty = useMemo(
    () => JSON.stringify(editedValues) !== JSON.stringify(initialValues),
    [editedValues, initialValues],
  );

  const handleSave = () => {
    if (!isDirty) return;
    onSave(editedValues);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <TextField
        label="Name"
        value={editedValues.name}
        onChange={(e) =>
          setEditedValues((prev) => ({ ...prev, name: e.target.value }))
        }
      />
      <TextField
        label="Description"
        value={editedValues.description}
        onChange={(e) =>
          setEditedValues((prev) => ({
            ...prev,
            description: e.target.value,
          }))
        }
      />
      <Button variant="contained" onClick={handleSave} disabled={!isDirty}>
        Save
      </Button>
    </Box>
  );
};
```

### Dependent Field Validation

When one field depends on another, clearing the parent field should also reset the dependent field:

```typescript
const handleCategoryChange = (newCategory: string) => {
  setEditedValues((prev) => ({
    ...prev,
    category: newCategory,
    // Reset dependent field when parent changes
    subcategory: '',
  }));

  // Clear any error on the dependent field
  setError('subcategory', undefined);
};
```

### Bulk Edit Dirty Checking

For bulk edit scenarios (editing multiple rows), track changes per row:

```typescript
interface BulkEditState {
  editedRows: Record<string, Record<string, any>>;
  originalRows: Record<string, Record<string, any>>;
}

const getDirtyRows = (state: BulkEditState): string[] =>
  Object.keys(state.editedRows).filter(
    (rowId) =>
      JSON.stringify(state.editedRows[rowId]) !==
      JSON.stringify(state.originalRows[rowId]),
  );

const hasDirtyRows = (state: BulkEditState): boolean =>
  getDirtyRows(state).length > 0;
```

## Best Practices

1. **Validate at multiple layers.** Utility validators catch format errors. Component validation prevents bad submissions. Thunk pre-validation catches invalid state. Each layer serves a different purpose.

2. **Use typed error objects.** Define error state with the same keys as the form interface (`{ [k in keyof FormType]?: string }`). This ensures every error maps to a real field and TypeScript catches typos.

3. **Return `undefined` for valid fields, strings for errors.** This convention lets you use `errors.fieldName !== undefined` as a boolean check, which maps directly to MUI `TextField`'s `error` prop.

4. **Clear errors on input change.** Do not wait until the next submission attempt to remove error messages. Clear the error for a field as soon as the user begins editing it.

5. **Use `rejectWithValue` for thunk validation failures.** This provides a typed, predictable error string that reducers and components can handle. Reserve thrown errors for truly unexpected failures.

6. **Keep validators pure.** Validation utility functions should have no side effects (no toasts, no state mutations). Let the calling code decide how to present errors to the user.

7. **Use `JSON.stringify` for dirty checking.** It is a simple and reliable approach for shallow-to-moderate object comparison. For deeply nested or large objects, consider a library like `lodash.isEqual`.

8. **Validate before dispatching.** Perform component-level validation before calling `dispatch`. This avoids unnecessary network requests and gives immediate feedback to the user.

9. **Show errors with toast for system-level failures.** Use `react-toastify` for errors that come from the Redux layer (rejected thunks, network issues). Use inline `helperText` on `TextField` for field-level validation errors.

10. **Enforce file constraints early.** Validate file names and counts in the dropzone `validator` callback, before files reach component state. This prevents invalid files from appearing in the UI at all.
