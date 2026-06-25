# App with Code Engine Functions

A complete example of a Domo Custom App that calls Code Engine serverless functions via package mappings. Demonstrates email notifications, external API integration, and dataset operations — all triggered from the app UI.

## Use Case

An order management app where:
- Users can submit orders that trigger a processing function
- Email notifications are sent on order status changes
- An external pricing API is called to validate quotes
- Order data is written to a Domo dataset for reporting

## Project Structure

```
order-manager/
├── public/
│   ├── manifest.json
│   └── thumbnail.png
├── src/
│   ├── components/
│   │   ├── OrderForm.tsx
│   │   ├── OrderList.tsx
│   │   └── PriceQuote.tsx
│   ├── services/
│   │   ├── codeEngineService.ts
│   │   └── orderService.ts
│   ├── reducers/
│   │   ├── index.ts
│   │   └── orders/
│   ├── types/
│   │   └── index.ts
│   └── index.tsx
└── package.json
```

## manifest.json

```json
{
  "name": "Order Manager",
  "version": "1.0.0",
  "size": { "width": 8, "height": 6 },
  "fullpage": true,
  "mapping": [
    {
      "dataSetId": "your-orders-dataset-id",
      "alias": "OrdersData",
      "fields": []
    }
  ],
  "collections": [
    {
      "name": "Orders",
      "syncEnabled": true,
      "schema": {
        "columns": [
          { "name": "orderId", "type": "STRING" },
          { "name": "customerName", "type": "STRING" },
          { "name": "customerEmail", "type": "STRING" },
          { "name": "items", "type": "STRING" },
          { "name": "totalAmount", "type": "STRING" },
          { "name": "status", "type": "STRING" },
          { "name": "notes", "type": "STRING" }
        ]
      },
      "defaultPermission": [
        "READ", "READ_CONTENT", "CREATE_CONTENT", "UPDATE_CONTENT"
      ]
    }
  ],
  "packageMapping": [
    {
      "alias": "processOrder",
      "parameters": [
        {
          "alias": "params",
          "type": "object",
          "nullable": false,
          "isList": false,
          "children": null
        }
      ],
      "output": {
        "alias": "returnValue",
        "type": "object",
        "children": null
      }
    },
    {
      "alias": "sendNotification",
      "parameters": [
        {
          "alias": "params",
          "type": "object",
          "nullable": false,
          "isList": false,
          "children": null
        }
      ],
      "output": {
        "alias": "returnValue",
        "type": "object",
        "children": null
      }
    },
    {
      "alias": "getPriceQuote",
      "parameters": [
        {
          "alias": "params",
          "type": "object",
          "nullable": false,
          "isList": false,
          "children": null
        }
      ],
      "output": {
        "alias": "returnValue",
        "type": "object",
        "children": null
      }
    }
  ]
}
```

## Code Engine Functions

These functions need to be deployed as a Code Engine package before the app can call them. See `references/code-engine-patterns.md` for the full deployment workflow.

### order-backend package (JavaScript)

```javascript
const codeengine = require('codeengine');

class Helpers {
  static async handleRequest(method, url, body = null, headers = {}) {
    const res = await codeengine.sendRequest(method, url, body, { headers });
    if (res.status >= 400) throw new Error(`${method} ${url}: ${res.status}`);
    return res.body ? JSON.parse(res.body) : null;
  }
}

// Process an order: validate, assign ID, update dataset
async function processOrder(params) {
  const { customerName, customerEmail, items, totalAmount } = params;

  if (!customerName || !items || !totalAmount) {
    return { success: false, error: 'Missing required fields' };
  }

  // Generate order ID
  const orderId = `ORD-${Date.now()}`;

  // Write to dataset for reporting
  const csvRow = [orderId, customerName, customerEmail, totalAmount, 'pending', new Date().toISOString()]
    .map(v => `"${String(v).replace(/"/g, '""')}"`)
    .join(',');

  try {
    await codeengine.sendRequest(
      'POST',
      `api/data/v3/datasources/${params.datasetId}/executions/upload?updateMethod=APPEND`,
      csvRow,
      { headers: { 'content-type': 'text/csv' } }
    );
  } catch (err) {
    console.log('Dataset write failed:', err.message);
    // Continue — dataset write is non-critical
  }

  return {
    success: true,
    orderId,
    status: 'pending',
    message: `Order ${orderId} created successfully`,
  };
}

// Send email notification
function sendNotification(params) {
  const { to, subject, body } = params;

  const emailBody = {
    parameters: {
      subject: subject,
      text: body,
      recipientsUserIds: [],
    },
  };
  const url = `/api/social/v3/messages/plainText/send?route=recipients&method=EMAIL&recipients=${to}`;

  return codeengine
    .sendRequest('post', url, emailBody, null, null)
    .then(() => ({ success: true }))
    .catch((reason) => {
      console.log('Email failed:', reason);
      return { success: false, error: String(reason) };
    });
}

// Get price quote from external pricing service
async function getPriceQuote(params) {
  const { items } = params;

  if (!items || !Array.isArray(items)) {
    return { success: false, error: 'items must be an array' };
  }

  // Simulate pricing logic (replace with actual external API call)
  const pricing = items.map(item => ({
    itemId: item.id,
    name: item.name,
    quantity: item.quantity,
    unitPrice: item.basePrice * (1 - (item.discount || 0)),
    lineTotal: item.quantity * item.basePrice * (1 - (item.discount || 0)),
  }));

  const subtotal = pricing.reduce((sum, item) => sum + item.lineTotal, 0);
  const tax = subtotal * 0.08;
  const total = subtotal + tax;

  return {
    success: true,
    lineItems: pricing,
    subtotal: Math.round(subtotal * 100) / 100,
    tax: Math.round(tax * 100) / 100,
    total: Math.round(total * 100) / 100,
    validUntil: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  };
}

module.exports = { processOrder, sendNotification, getPriceQuote };
```

### Function Manifest

```json
[
  {
    "name": "processOrder",
    "displayName": "Process Order",
    "description": "Validate and process a new order",
    "inputs": [
      { "name": "params", "displayName": "Order Parameters", "type": "object", "nullable": false, "isList": false }
    ],
    "output": { "name": "returnValue", "displayName": "Result", "type": "object", "nullable": false, "isList": false }
  },
  {
    "name": "sendNotification",
    "displayName": "Send Notification",
    "description": "Send an email notification",
    "inputs": [
      { "name": "params", "displayName": "Email Parameters", "type": "object", "nullable": false, "isList": false }
    ],
    "output": { "name": "returnValue", "displayName": "Result", "type": "object", "nullable": false, "isList": false }
  },
  {
    "name": "getPriceQuote",
    "displayName": "Get Price Quote",
    "description": "Calculate pricing for a list of items",
    "inputs": [
      { "name": "params", "displayName": "Quote Parameters", "type": "object", "nullable": false, "isList": false }
    ],
    "output": { "name": "returnValue", "displayName": "Result", "type": "object", "nullable": false, "isList": false }
  }
]
```

## types/index.ts

```typescript
export interface OrderItem {
  id: string;
  name: string;
  quantity: number;
  basePrice: number;
  discount?: number;
}

export interface OrderData {
  orderId: string;
  customerName: string;
  customerEmail: string;
  items: string; // JSON-stringified OrderItem[]
  totalAmount: string;
  status: string;
  notes: string;
}

export interface Order extends OrderData {
  id: string; // AppDB document ID
}

export interface PriceQuote {
  lineItems: {
    itemId: string;
    name: string;
    quantity: number;
    unitPrice: number;
    lineTotal: number;
  }[];
  subtotal: number;
  tax: number;
  total: number;
  validUntil: string;
}

export interface CodeEngineResponse<T> {
  returnValue: T;
}
```

## services/codeEngineService.ts

This service wraps all Code Engine function calls. The pattern is always:
1. POST to `/domo/codeengine/v2/packages/{alias}`
2. Pass parameters in `{ params: { ... } }`
3. Response comes back as `{ returnValue: { ... } }`

```typescript
import domo from 'ryuu.js';
import { OrderItem, PriceQuote, CodeEngineResponse } from '../types';

const CE_BASE = '/domo/codeengine/v2/packages';

export const codeEngineService = {
  /**
   * Process a new order via Code Engine
   */
  async processOrder(
    customerName: string,
    customerEmail: string,
    items: OrderItem[],
    totalAmount: number
  ) {
    const response = await domo.post<
      CodeEngineResponse<{
        success: boolean;
        orderId?: string;
        status?: string;
        message?: string;
        error?: string;
      }>
    >(`${CE_BASE}/processOrder`, {
      params: {
        customerName,
        customerEmail,
        items,
        totalAmount,
      },
    });

    if (!response.returnValue.success) {
      throw new Error(response.returnValue.error || 'Order processing failed');
    }

    return response.returnValue;
  },

  /**
   * Send an email notification via Code Engine
   */
  async sendNotification(to: string, subject: string, body: string) {
    const response = await domo.post<
      CodeEngineResponse<{ success: boolean; error?: string }>
    >(`${CE_BASE}/sendNotification`, {
      params: { to, subject, body },
    });

    return response.returnValue;
  },

  /**
   * Get a price quote for a list of items
   */
  async getPriceQuote(items: OrderItem[]): Promise<PriceQuote> {
    const response = await domo.post<
      CodeEngineResponse<PriceQuote & { success: boolean; error?: string }>
    >(`${CE_BASE}/getPriceQuote`, {
      params: { items },
    });

    if (!response.returnValue.success) {
      throw new Error(response.returnValue.error || 'Quote failed');
    }

    return response.returnValue;
  },
};
```

## services/orderService.ts

Combines AppDB storage with Code Engine calls:

```typescript
import { AppDBClient, AppDBDocument } from '@domoinc/toolkit';
import { OrderData, Order, OrderItem } from '../types';
import { codeEngineService } from './codeEngineService';

const COLLECTION = 'Orders';
const OrdersClient = new AppDBClient.DocumentsClient<OrderData>(COLLECTION);

const extractDocs = <T>(response: { data: AppDBDocument<T>[] }): (T & { id: string })[] =>
  response.data.map(doc => ({ id: doc.id, ...doc.content }));

export const orderService = {
  async getAll(): Promise<Order[]> {
    return extractDocs<OrderData>(await OrdersClient.get({}, {}));
  },

  async getByStatus(status: string): Promise<Order[]> {
    const queryParams = { 'content.status': { $eq: status } };
    return extractDocs<OrderData>(await OrdersClient.get(queryParams, {}));
  },

  /**
   * Submit a new order:
   * 1. Get price quote from Code Engine
   * 2. Process the order via Code Engine
   * 3. Save to AppDB
   * 4. Send notification
   */
  async submitOrder(
    customerName: string,
    customerEmail: string,
    items: OrderItem[],
    notes: string
  ): Promise<Order> {
    // Step 1: Get pricing
    const quote = await codeEngineService.getPriceQuote(items);

    // Step 2: Process order
    const result = await codeEngineService.processOrder(
      customerName,
      customerEmail,
      items,
      quote.total
    );

    // Step 3: Save to AppDB
    const order = extractDocs<OrderData>(
      await OrdersClient.create({
        orderId: result.orderId!,
        customerName,
        customerEmail,
        items: JSON.stringify(items),
        totalAmount: String(quote.total),
        status: 'pending',
        notes,
      })
    )[0];

    // Step 4: Send confirmation (fire-and-forget)
    codeEngineService
      .sendNotification(
        customerEmail,
        `Order ${result.orderId} Confirmed`,
        `Your order for $${quote.total} has been received and is being processed.`
      )
      .catch(console.error); // Don't fail the order if email fails

    return order;
  },

  async updateStatus(id: string, newStatus: string, customerEmail: string): Promise<void> {
    const response = await OrdersClient.get({}, {});
    const doc = response.data.find(d => d.id === id);
    if (!doc) throw new Error('Order not found');

    await OrdersClient.update(id, {
      ...doc.content,
      status: newStatus,
    });

    // Notify customer of status change
    codeEngineService
      .sendNotification(
        customerEmail,
        `Order ${doc.content.orderId} Status Update`,
        `Your order status has been updated to: ${newStatus}`
      )
      .catch(console.error);
  },
};
```

## components/PriceQuote.tsx

```typescript
import React, { useState } from 'react';
import { codeEngineService } from '../services/codeEngineService';
import { OrderItem, PriceQuote as PriceQuoteType } from '../types';
import {
  Box, Button, Typography, Table, TableHead, TableRow,
  TableCell, TableBody, CircularProgress, Alert,
} from '@mui/material';

interface Props {
  items: OrderItem[];
  onConfirm: (quote: PriceQuoteType) => void;
}

export const PriceQuote: React.FC<Props> = ({ items, onConfirm }) => {
  const [quote, setQuote] = useState<PriceQuoteType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGetQuote = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await codeEngineService.getPriceQuote(items);
      setQuote(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get quote');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <CircularProgress />;

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!quote ? (
        <Button variant="outlined" onClick={handleGetQuote}>
          Get Price Quote
        </Button>
      ) : (
        <Box>
          <Typography variant="h6" gutterBottom>Price Quote</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Item</TableCell>
                <TableCell align="right">Qty</TableCell>
                <TableCell align="right">Unit Price</TableCell>
                <TableCell align="right">Total</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {quote.lineItems.map(item => (
                <TableRow key={item.itemId}>
                  <TableCell>{item.name}</TableCell>
                  <TableCell align="right">{item.quantity}</TableCell>
                  <TableCell align="right">${item.unitPrice.toFixed(2)}</TableCell>
                  <TableCell align="right">${item.lineTotal.toFixed(2)}</TableCell>
                </TableRow>
              ))}
              <TableRow>
                <TableCell colSpan={3} align="right"><strong>Subtotal</strong></TableCell>
                <TableCell align="right">${quote.subtotal.toFixed(2)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell colSpan={3} align="right">Tax</TableCell>
                <TableCell align="right">${quote.tax.toFixed(2)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell colSpan={3} align="right"><strong>Total</strong></TableCell>
                <TableCell align="right"><strong>${quote.total.toFixed(2)}</strong></TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Valid until {new Date(quote.validUntil).toLocaleDateString()}
          </Typography>
          <Button
            variant="contained"
            onClick={() => onConfirm(quote)}
            sx={{ mt: 2 }}
          >
            Confirm & Submit Order
          </Button>
        </Box>
      )}
    </Box>
  );
};
```

## Deploying the Code Engine Functions

Before the app can call these functions, deploy them using MCP tools:

```
# 1. Create the Code Engine package
codeengine_package_create(
  name: "order-backend",
  description: "Backend functions for Order Manager app",
  code: "<the JavaScript code above>",
  functions: [
    { name: "processOrder", displayName: "Process Order", ... },
    { name: "sendNotification", displayName: "Send Notification", ... },
    { name: "getPriceQuote", displayName: "Get Price Quote", ... }
  ]
)

# 2. Release the package
codeengine_version_release(package_id, version=1)

# 3. Verify deployment
codeengine_package_get(package_id)
```

Then publish the app:

```
# 4. Validate manifest
procode_manifest_validate(manifest)

# 5. Build and publish
yarn build
cd build && domo publish && cd ..
```

## Key Patterns

1. **Service Wrapper** — All Code Engine calls go through `codeEngineService.ts`, never called directly from components
2. **Typed Responses** — Use `CodeEngineResponse<T>` generic for type-safe return values
3. **Fire-and-Forget Notifications** — Email sends use `.catch(console.error)` to avoid blocking the main flow
4. **Multi-Step Workflows** — Order submission chains: quote → process → save to AppDB → notify
5. **Error Handling** — Check `returnValue.success` on every response; throw on failure
6. **JSON in STRING** — Complex data (item arrays) stored as JSON strings in AppDB `STRING` columns
7. **Package Mapping Pattern** — Every function uses `{ alias, parameters: [{ alias: "params", type: "object" }], output: { alias: "returnValue", type: "object" } }` — this is the standard format
8. **Base URL Constant** — `const CE_BASE = '/domo/codeengine/v2/packages'` used consistently
9. **Dataset Integration** — Code Engine functions can write to Domo datasets for reporting alongside AppDB for app state
10. **Deploy Before Use** — Code Engine functions must be created and released before the app can call them
