# Simple Domo App Example

A minimal example showing common Domo App patterns.

## Project Structure

```
simple-task-app/
├── public/
│   ├── manifest.json
│   └── thumbnail.png
├── src/
│   ├── components/
│   │   ├── TaskList.tsx
│   │   └── TaskForm.tsx
│   ├── services/
│   │   └── taskService.ts
│   ├── reducers/
│   │   ├── index.ts          # Store config + typed hooks
│   │   └── tasks/
│   │       ├── actions.ts    # Async thunks
│   │       ├── reducer.ts    # createReducer
│   │       └── selectors.ts  # State selectors
│   └── index.tsx
└── package.json
```

## manifest.json

```json
{
  "name": "Task Manager",
  "version": "1.0.0",
  "size": { "width": 8, "height": 6 },
  "fullpage": false,
  "collections": [
    {
      "name": "Tasks",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "title", "type": "STRING" },
          { "name": "completed", "type": "STRING" },
          { "name": "dueDate", "type": "STRING" }
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

## taskService.ts

```typescript
import { AppDBClient, AppDBDocument } from '@domoinc/toolkit';

const COLLECTION = 'Tasks';

// Data model (without metadata)
export interface TaskData {
  title: string;
  completed: boolean;
  dueDate: string;
}

// Full document model (with metadata)
export interface Task extends TaskData {
  id: string;
}

// Create typed client
const TasksClient = new AppDBClient.DocumentsClient<TaskData>(COLLECTION);

// Helper to extract task data with ID
const extractTasks = (response: { data: AppDBDocument<TaskData>[] }): Task[] =>
  response.data.map(doc => ({
    id: doc.id,
    title: doc.content.title,
    completed: doc.content.completed,
    dueDate: doc.content.dueDate,
  }));

export const taskService = {
  async getAll(): Promise<Task[]> {
    const response = await TasksClient.get({}, {});
    return extractTasks(response);
  },

  async create(title: string, dueDate: string): Promise<Task> {
    const response = await TasksClient.create({
      title,
      completed: false,
      dueDate
    });
    return extractTasks(response)[0];
  },

  async update(id: string, updates: Partial<TaskData>): Promise<void> {
    // Get current task
    const response = await TasksClient.get({}, {});
    const task = response.data.find(doc => doc.id === id);

    if (!task) throw new Error('Task not found');

    // Update with merged content
    await TasksClient.update(id, {
      ...task.content,
      ...updates
    });
  },

  async delete(id: string): Promise<void> {
    await TasksClient.delete(id);
  },

  async toggleComplete(id: string): Promise<void> {
    // Get current task
    const response = await TasksClient.get({}, {});
    const task = response.data.find(doc => doc.id === id);

    if (!task) throw new Error('Task not found');

    await this.update(id, {
      completed: !task.content.completed
    });
  }
};
```

## reducers/tasks/actions.ts

```typescript
import { createAsyncThunk } from '@reduxjs/toolkit';
import { taskService } from 'services/taskService';

export const fetchTasks = createAsyncThunk(
  'FETCH_TASKS',
  taskService.getAll
);

export const createTask = createAsyncThunk(
  'CREATE_TASK',
  async ({ title, dueDate }: { title: string; dueDate: string }) => {
    return await taskService.create(title, dueDate);
  }
);

export const toggleTask = createAsyncThunk(
  'TOGGLE_TASK',
  async (id: string) => {
    await taskService.toggleComplete(id);
    return id;
  }
);

export const deleteTask = createAsyncThunk(
  'DELETE_TASK',
  async (id: string) => {
    await taskService.delete(id);
    return id;
  }
);
```

## reducers/tasks/reducer.ts

```typescript
import { createReducer } from '@reduxjs/toolkit';
import { Task } from 'services/taskService';
import { fetchTasks, createTask, toggleTask, deleteTask } from './actions';

interface TasksState {
  items: Task[];
  loading: {
    fetch: number;
  };
  error: string | null;
}

const initialState: TasksState = {
  items: [],
  loading: {
    fetch: 0,
  },
  error: null,
};

const TasksReducer = createReducer(initialState, (builder) => {
  // Fetch tasks
  builder.addCase(fetchTasks.pending, (state) => {
    state.loading.fetch += 1;
    state.error = null;
  });
  builder.addCase(fetchTasks.fulfilled, (state, { payload }) => {
    state.items = payload;
    state.loading.fetch -= 1;
  });
  builder.addCase(fetchTasks.rejected, (state, { error }) => {
    state.loading.fetch -= 1;
    state.error = error.message || 'Failed to fetch tasks';
  });

  // Create task
  builder.addCase(createTask.fulfilled, (state, { payload }) => {
    state.items.push(payload);
  });

  // Toggle task
  builder.addCase(toggleTask.fulfilled, (state, { payload: id }) => {
    const task = state.items.find(t => t.id === id);
    if (task) {
      task.completed = !task.completed;
    }
  });

  // Delete task
  builder.addCase(deleteTask.fulfilled, (state, { payload: id }) => {
    state.items = state.items.filter(t => t.id !== id);
  });

  builder.addDefaultCase((state) => state);
});

export default TasksReducer;
```

## reducers/tasks/selectors.ts

```typescript
import { RootState } from 'reducers';

export const selectTasks = (state: RootState) => state.Tasks.items;
export const selectTasksLoading = (state: RootState) => state.Tasks.loading.fetch > 0;
export const selectTasksError = (state: RootState) => state.Tasks.error;
```

## reducers/index.ts (Store)

```typescript
import {
  Action,
  configureStore,
  ThunkAction,
} from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import TasksReducer from './tasks/reducer';

export const store = configureStore({
  reducer: {
    Tasks: TasksReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  Action<string>
>;

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
```

## TaskList.tsx

```typescript
import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from 'reducers';
import { fetchTasks, toggleTask, deleteTask } from 'reducers/tasks/actions';
import { selectTasks, selectTasksLoading, selectTasksError } from 'reducers/tasks/selectors';
import { Box, List, ListItem, ListItemText, Checkbox, IconButton, CircularProgress } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';

export const TaskList: React.FC = () => {
  const dispatch = useAppDispatch();
  const tasks = useAppSelector(selectTasks);
  const loading = useAppSelector(selectTasksLoading);
  const error = useAppSelector(selectTasksError);

  useEffect(() => {
    dispatch(fetchTasks());
  }, [dispatch]);

  if (loading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Box color="error.main">{error}</Box>;
  }

  return (
    <List>
      {tasks.map((task) => (
        <ListItem
          key={task.id}
          secondaryAction={
            <IconButton
              edge="end"
              onClick={() => dispatch(deleteTask(task.id))}
            >
              <DeleteIcon />
            </IconButton>
          }
        >
          <Checkbox
            checked={task.completed}
            onChange={() => dispatch(toggleTask(task.id))}
          />
          <ListItemText
            primary={task.title}
            secondary={new Date(task.dueDate).toLocaleDateString()}
            sx={{
              textDecoration: task.completed ? 'line-through' : 'none'
            }}
          />
        </ListItem>
      ))}
    </List>
  );
};
```

## TaskForm.tsx

```typescript
import React, { useState } from 'react';
import { useAppDispatch } from 'reducers';
import { createTask } from 'reducers/tasks/actions';
import { Box, TextField, Button } from '@mui/material';

export const TaskForm: React.FC = () => {
  const dispatch = useAppDispatch();
  const [title, setTitle] = useState('');
  const [dueDate, setDueDate] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !dueDate) return;

    await dispatch(createTask({ title, dueDate }));
    setTitle('');
    setDueDate('');
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mb: 2 }}>
      <TextField
        fullWidth
        label="Task Title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        sx={{ mb: 1 }}
      />
      <TextField
        fullWidth
        type="date"
        label="Due Date"
        value={dueDate}
        onChange={(e) => setDueDate(e.target.value)}
        InputLabelProps={{ shrink: true }}
        sx={{ mb: 1 }}
      />
      <Button type="submit" variant="contained" fullWidth>
        Add Task
      </Button>
    </Box>
  );
};
```

## index.tsx

```typescript
import React from 'react';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import { store } from './reducers';
import { TaskForm } from './components/TaskForm';
import { TaskList } from './components/TaskList';
import { Container, Typography, Box } from '@mui/material';

const App = () => (
  <Container maxWidth="md" sx={{ py: 4 }}>
    <Typography variant="h4" gutterBottom>
      Task Manager
    </Typography>
    <Box sx={{ mb: 4 }}>
      <TaskForm />
    </Box>
    <TaskList />
  </Container>
);

ReactDOM.render(
  <Provider store={store}>
    <App />
  </Provider>,
  document.getElementById('root')
);
```

## package.json Scripts

```json
{
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "upload": "yarn build && cd build && domo publish && cd ..",
    "prestart": "da apply-manifest start",
    "postbuild": "da apply-manifest build"
  }
}
```

## Workflow

```bash
# Initial setup
da new task-manager
cd task-manager

# Install dependencies
yarn install

# Login to Domo
domo login -i company.domo.com

# Start development
yarn start

# When ready to deploy
yarn upload

# Copy app ID from build/manifest.json to public/manifest.json
```

## Key Patterns

1. **Service Layer** - Encapsulate all AppDB calls in service files using `AppDBClient`
2. **Typed Clients** - Use `AppDBClient.DocumentsClient<T>` for type safety
3. **Separate Files** - Split actions.ts, reducer.ts, selectors.ts per feature
4. **createReducer** - Use `createReducer` (not createSlice) with builder callback
5. **createAsyncThunk** - Use for all async operations calling services
6. **Typed Hooks** - Use `useAppDispatch` and `useAppSelector` (not plain hooks)
7. **Selectors** - Define selectors for accessing state from components
8. **Loading Counters** - Use increment/decrement counters for loading states
9. **Store in reducers/index.ts** - Centralize store config with typed exports
10. **MUI Components** - Use Material-UI for consistent styling
