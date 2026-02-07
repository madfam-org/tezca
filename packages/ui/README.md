# @tezca/ui

Shared UI component library for Leyes Como Código applications.

## Technologies
- React 19
- Tailwind CSS
- Class Variance Authority (CVA)
- Lucide React Icons

## Components
This package exports common UI primitives like:
- Button
- Card
- Badge
- Alert
- Input
- Select
- Progress

## Usage
Import components directly from the package:

```tsx
import { Button, Card } from "@tezca/ui";

export default function MyComponent() {
  return (
    <Card>
      <Button variant="default">Click Me</Button>
    </Card>
  );
}
```
