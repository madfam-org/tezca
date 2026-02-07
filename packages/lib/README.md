# @tezca/lib

Shared utilities and TypeScript types for Leyes Como Código applications.

## Contents

### Utilities
- `cn(...inputs)`: Utility for merging Tailwind classes safely (clsx + tailwind-merge).

### Types
Core domain types shared between API, Web, and Admin:
- `Law`
- `LawVersion`
- `IngestionStatus`
- `DashboardStats`

## Usage

```tsx
import { cn, type Law } from "@tezca/lib";

const myLaw: Law = { ... };

<div className={cn("p-4 bg-red-500", className)} />
```
