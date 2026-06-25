# Logging and Analytics Guide for Domo Custom Apps

## 1. Overview

Domo provides a built-in analytics API at `/domo/analytics/v1` for tracking user behavior, app performance, and errors within Custom Apps. Events are categorized into three types:

- **LOAD** -- App and page initialization events (e.g., app startup, identity resolution)
- **ACTION** -- User-initiated interactions (e.g., button clicks, file uploads, workflow triggers)
- **ERROR** -- Failures and exceptions caught during operations

All analytics calls are authenticated using the Ryuu token and tagged with a per-session UUID for correlating events within a single user session.

---

## 2. Analytics Service Setup

The analytics service is a standalone module that wraps raw `fetch` calls to the Domo analytics endpoint. It does **not** use `ryuu.js` or the `domo` library -- it calls the API directly.

```typescript
// services/analyticsService.ts

import { AnalyticsPropsShape } from 'models/types/analyticsTypes';
import { v4 } from 'uuid';

const token = window.__RYUU_AUTHENTICATION_TOKEN__;
const sessionId = v4();

const recordLoad = async (eventType: string, props: AnalyticsPropsShape) =>
  record('LOAD', { sessionId, eventType, ...props });

const recordAction = async (eventType: string, props: AnalyticsPropsShape) =>
  record('ACTION', { sessionId, eventType, ...props });

const recordError = async (eventType: string, props: AnalyticsPropsShape) =>
  record('ERROR', { sessionId, eventType, ...props });

const record = (
  actionType: string,
  properties: AnalyticsPropsShape & { sessionId: string; eventType: string },
) =>
  fetch(`/domo/analytics/v1`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-DOMO-Ryuu-Token': token,
    },
    body: JSON.stringify({ type: actionType, properties }),
  });

export const AnalyticsService = { recordLoad, recordAction, recordError };
```

Key details:

- **`window.__RYUU_AUTHENTICATION_TOKEN__`** is the auth token injected by the Domo runtime. It is read once at module load time.
- **`sessionId`** is a UUID v4 generated once per module initialization. It persists for the lifetime of the app session and is attached to every event, allowing you to correlate all events from a single user visit.
- **`record`** is the private core function. The three public methods (`recordLoad`, `recordAction`, `recordError`) are thin wrappers that set the `type` field.

---

## 3. Event Type Constants

Define all event types as a single `as const` object. This gives you autocomplete, type safety, and a single place to find every tracked event in the app.

```typescript
// constants/analyticsConstants.ts

export const ANALYTICS_EVENT_TYPES = {
  ADD_ATTACHMENT_BUTTON: 'ADD_ATTACHMENT_BUTTON',
  APP_LOAD: 'APP_LOAD',
  BULK_UPDATE: 'BULK_UPDATE',
  FILE_UPLOAD: 'FILE_UPLOAD',
  FILE_DELETION: 'FILE_DELETION',
  IDENTITY_LOAD: 'IDENTITY_LOAD',
  WORKFLOW_TRIGGERED: 'WORKFLOW_TRIGGERED',
  WORK_ITEM_UPDATE: 'WORK_ITEM_UDPATE',
  // Add new event types here as features are built
} as const;
```

Guidelines for naming event types:

- Use `SCREAMING_SNAKE_CASE`.
- Name them after the **action or lifecycle moment**, not the UI component (e.g., `WORKFLOW_TRIGGERED` not `WORKFLOW_BUTTON_CLICKED`).
- Keep them in a single constants file so the full list of tracked events is discoverable.

---

## 4. Property Keys

The Domo analytics API accepts a flat properties object. Use a constants map to refer to property slots by name rather than magic strings.

```typescript
// constants/analyticsConstants.ts

export const ANALYTICS_PROP_KEYS: { [k: string]: AnalyticsValidKeys } = {
  PROP1: '"Property 1"',
  PROP2: '"Property 2"',
  PROP3: '"Property 3"',
  PROP4: '"Property 4"',
  PROP5: '"Property 5"',
  PROP6: '"Property 6"',
} as const;
```

Establish a consistent assignment of meaning to each property slot and document it:

| Prop Key | Typical Usage |
|----------|---------------|
| PROP1 | User ID / identity |
| PROP2 | General context |
| PROP3 | General context |
| PROP4 | Entity IDs (e.g., comma-separated work item UIDs) |
| PROP5 | User email or error message |
| PROP6 | Descriptive label (e.g., workflow name and version) |

The same property slot can carry different data depending on the event type, but try to keep the semantics consistent within an event category (LOAD, ACTION, ERROR) to make analytics queries easier.

---

## 5. Types

Define types for the analytics property shape and the valid key strings.

```typescript
// models/types/analyticsTypes.ts

export type AnalyticsValidKeys =
  | '"Property 1"'
  | '"Property 2"'
  | '"Property 3"'
  | '"Property 4"'
  | '"Property 5"'
  | '"Property 6"';

export type AnalyticsPropsShape = {
  [key in AnalyticsValidKeys]?: string;
};
```

The `AnalyticsPropsShape` type ensures you can only pass recognized property keys. All values are optional strings.

---

## 6. Usage Patterns

### recordLoad -- Initialization Events

Use `recordLoad` when the app or a major section finishes loading. This is typically called once during startup.

```typescript
AnalyticsService.recordLoad(ANALYTICS_EVENT_TYPES.APP_LOAD, {
  [ANALYTICS_PROP_KEYS.PROP1]: identity.userId,
} as AnalyticsPropsShape);
```

```typescript
AnalyticsService.recordLoad(ANALYTICS_EVENT_TYPES.IDENTITY_LOAD, {
  [ANALYTICS_PROP_KEYS.PROP1]: identity.userId,
  [ANALYTICS_PROP_KEYS.PROP5]: identity.email,
} as AnalyticsPropsShape);
```

### recordAction -- User Interactions

Use `recordAction` when the user performs a meaningful operation. Include enough context in the properties to understand what happened.

```typescript
AnalyticsService.recordAction(ANALYTICS_EVENT_TYPES.WORKFLOW_TRIGGERED, {
  [ANALYTICS_PROP_KEYS.PROP4]: workItems.map(({ UID }) => UID).join(','),
  [ANALYTICS_PROP_KEYS.PROP5]: userEmail,
  [ANALYTICS_PROP_KEYS.PROP6]: `${workflowName} (${workflowId}/${workflowVersion})`,
} as AnalyticsPropsShape);
```

```typescript
AnalyticsService.recordAction(ANALYTICS_EVENT_TYPES.FILE_UPLOAD, {
  [ANALYTICS_PROP_KEYS.PROP1]: userId,
  [ANALYTICS_PROP_KEYS.PROP2]: fileName,
} as AnalyticsPropsShape);
```

### recordError -- Error Tracking

Use `recordError` inside `catch` blocks to track failures. Always include the error message in the properties.

```typescript
AnalyticsService.recordError(ANALYTICS_EVENT_TYPES.FILE_UPLOAD, {
  [ANALYTICS_PROP_KEYS.PROP5]: error,
} as AnalyticsPropsShape);
```

---

## 7. Integration with Error Handling

The standard pattern is to wrap operations in try/catch and pair the success analytics call with an error analytics call using the **same event type**. This makes it straightforward to compare success vs. failure rates for any given operation.

```typescript
try {
  const result = await performOperation(params);

  AnalyticsService.recordAction(ANALYTICS_EVENT_TYPES.BULK_UPDATE, {
    [ANALYTICS_PROP_KEYS.PROP1]: userId,
    [ANALYTICS_PROP_KEYS.PROP4]: itemIds.join(','),
  } as AnalyticsPropsShape);

  return result;
} catch (error) {
  AnalyticsService.recordError(ANALYTICS_EVENT_TYPES.BULK_UPDATE, {
    [ANALYTICS_PROP_KEYS.PROP1]: userId,
    [ANALYTICS_PROP_KEYS.PROP5]: String(error),
  } as AnalyticsPropsShape);

  throw error;
}
```

Key points:

- Use the **same event type** for both the action and error calls so they can be correlated in analytics.
- Convert the error to a string with `String(error)` before passing it as a property value.
- Re-throw the error after recording it if the caller needs to handle it.
- The analytics `fetch` call itself is fire-and-forget. It should not block the operation or cause a secondary failure if the analytics endpoint is unavailable.

---

## 8. Console Logging

Use console logging sparingly and with intention. It is a development and debugging aid, not a replacement for analytics.

### console.warn -- Non-Critical Recoverable Issues

Use `console.warn` when an operation fails but the app can continue normally. Common in storage services where a cache miss or stale data is not fatal.

```typescript
try {
  const cached = await storageService.get(key);
  return cached;
} catch (e) {
  console.warn(e);
  return fallbackValue;
}
```

### console.error -- Debugging Critical Failures

Use `console.error` when something unexpected fails and you want visibility during development. Include a descriptive message string before the error object.

```typescript
try {
  const parsed = parseEmailBody(rawHtml);
  return parsed;
} catch (e) {
  console.error('Failed to parse email body', e);
  return null;
}
```

### When to Use Which

| Scenario | Method |
|----------|--------|
| Cache miss or stale data | `console.warn` |
| Optional feature fails silently | `console.warn` |
| Unexpected parse/transform failure | `console.error` |
| API call failure during development | `console.error` |
| Tracking user behavior | `AnalyticsService.recordAction` |
| Tracking operation failures in production | `AnalyticsService.recordError` |

Console methods are stripped or ignored in production Domo environments. Use `AnalyticsService` for anything you need to observe in production.

---

## 9. Best Practices

1. **Always pair analytics with try/catch.** Every service method that can fail should record both the success action and the error with the same event type.

2. **Use the session ID for correlation.** The UUID generated at app startup ties together all events from a single visit. Do not generate a new session ID per call.

3. **Keep property assignments consistent.** Document which PROP slot means what for each event type. Inconsistent property usage makes analytics queries painful.

4. **Fire and forget.** Do not `await` analytics calls in the critical path. The `record` function returns a promise, but callers should not block on it or handle its rejection.

5. **Use raw fetch for analytics.** The analytics service uses `fetch` directly with the Ryuu token header rather than the `domo` library. This avoids coupling the analytics layer to the data access layer.

6. **Define event types as constants.** Never use inline strings for event types. The `as const` assertion gives you a union type that catches typos at compile time.

7. **Convert errors to strings.** The properties object expects string values. Always convert error objects with `String(error)` or access `error.message` before passing them to `recordError`.

8. **Reserve console logging for development.** Use `console.warn` for recoverable issues and `console.error` for unexpected failures. Use `AnalyticsService` for production observability.

9. **Log enough context to be useful.** Include user IDs, entity IDs, workflow names, and versions in analytics properties. A bare event type with no properties is hard to act on.

10. **Keep the analytics service stateless.** Beyond the session ID, the service should not hold mutable state. Each call should be self-contained with all context passed through parameters.
