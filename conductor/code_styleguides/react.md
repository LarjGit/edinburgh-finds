# React Code Style Guide

## General Principles
- **Functional Components:** Use functional components with Hooks for all new components. Avoid class components.
- **Strict Mode:** Ensure `React.StrictMode` is enabled in the application root.
- **Composition over Inheritance:** Use component composition to reuse code.

## File Structure & Naming
- **PascalCase:** Use PascalCase for component filenames and component names (e.g., `UserProfile.tsx`).
- **One Component Per File:** Generally, define one main component per file. Small, strictly related internal components are acceptable in the same file.
- **Directory Structure:** Group related components in folders. Use an `index.ts` (barrel file) only if necessary for cleaner imports.

## TypeScript Usage
- **Interfaces for Props:** Use `interface` to define prop types. Name them `[ComponentName]Props`.
  ```typescript
  interface ButtonProps {
    label: string;
    onClick: () => void;
  }
  ```
- **No `any`:** Avoid using `any`. Use specific types or `unknown` with narrowing.
- **Event Types:** Use React's strict event types (e.g., `React.ChangeEvent<HTMLInputElement>`).

## Hooks
- **Rules of Hooks:** Always call hooks at the top level of the function. Never inside loops, conditions, or nested functions.
- **Custom Hooks:** Prefix custom hooks with `use` (e.g., `useWindowSize`).
- **exhaustive-deps:** Respect the `react-hooks/exhaustive-deps` ESLint rule. Do not suppress it without a critical reason.

## State Management
- **Local State:** Use `useState` for simple, local UI state.
- **Complex State:** Use `useReducer` for complex state logic involving multiple sub-values.
- **Context:** Use `useContext` for global state like theme or user authentication, but avoid overusing it to prevent unnecessary re-renders.

## Performance
- **Memoization:** Use `useMemo` and `useCallback` only when necessary (e.g., passing functions to optimized child components or expensive calculations). Premature optimization can add complexity.
- **Code Splitting:** Use `React.lazy` and `Suspense` for route-based code splitting.

## Styling (Tailwind CSS)
- **Utility First:** Use Tailwind utility classes directly in the `className` prop.
- **clsx / tailwind-merge:** Use `clsx` or `tailwind-merge` for conditional class logic, especially for reusable components.

## Testing
- **React Testing Library:** Use `drtl` (React Testing Library) for testing components.
- **Behavior Driven:** Test how the user interacts with the component, not the implementation details (e.g., "User clicks button" vs "State x changes to y").
