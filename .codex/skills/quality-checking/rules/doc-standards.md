# Documentation Quality Standards

## Required Elements Per Endpoint

Each endpoint documentation MUST include:

- [ ] HTTP method (GET/POST/PUT/DELETE/PATCH)
- [ ] Full path (e.g., `/api/products/:id`)
- [ ] Brief description (1-2 sentences)
- [ ] Parameters table (if any)
- [ ] Response status codes
- [ ] At least one response example

## Authentication Markers

- If a route uses `requireAuth` middleware → mark with 🔒
- If a route uses `isAdmin` middleware → mark with 🔒 (Admin)
- If no auth middleware → do NOT add any auth marker

## Format Rules

- Group endpoints by resource (products, categories, etc.)
- Order endpoints: GET (list) → GET (single) → POST → PUT → DELETE
- Use consistent heading levels: `###` for each endpoint
- JSON examples must be valid (parseable)

## Common Issues to Flag

- Missing auth marker when middleware is present
- Empty parameters table (should be omitted instead)
- Response example that doesn't match described schema
- Missing error response codes (400, 401, 404, 500)
