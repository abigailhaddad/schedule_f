# Schedule F Frontend

This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Refactoring Plan

### 1. State Management Refactoring

- Create a centralized `DataContext` to manage all table-related state:
  - Filters, sorting, pagination, and search query state
  - URL parameter syncing logic
  - Cached filtered/sorted data
  
```
src/contexts/DataContext.tsx
```

### 2. Component Decomposition

Break down large components into smaller, focused ones:

- Split `CommentTable.tsx` into:
  - `TableHeader.tsx` - search, column visibility, export
  - `ColumnManager.tsx` - column visibility logic
  - `TextHighlighter.tsx` - text highlighting logic
  - `TableCell.tsx` - rendering different cell types

### 3. Improved Caching Strategy

Implement a proper caching mechanism with invalidation:

```
src/lib/cache.ts
```

- Replace the simple timeout-based cache with LRU cache
- Add proper cache key generation and invalidation strategy
- Implement cache persistence between server restarts

### 4. Filter Architecture Improvements

Implement a FilterBuilder pattern for composable, testable filters:

```
src/lib/filters/FilterBuilder.ts
```

- Create reusable filter predicates
- Support complex filter compositions
- Make filter logic more testable

### 5. Server/Client Component Optimization

- Leverage Next.js server components for data fetching
- Push more rendering logic server-side
- Optimize client-side hydration

### 6. Testing Strategy

Improve test coverage and quality:

- Add unit tests for hooks and utility functions
- Create integration tests for filter combinations
- Test server actions with proper mocking
- Implement testing utilities for common patterns

## Implementation Phases

### Phase 1: Foundation

- Implement DataContext
- Create FilterBuilder
- Setup improved caching

### Phase 2: Component Refactoring

- Break down CommentTable
- Refactor FilterSection
- Optimize server/client component split

### Phase 3: Testing & Optimization

- Implement comprehensive test suite
- Performance optimization
- Documentation

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!