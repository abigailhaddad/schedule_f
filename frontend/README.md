# Schedule F Frontend

This is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Project Overview

The Schedule F Frontend is a web application designed to [**Please add a brief description of the project's purpose and target audience here**]. It utilizes a modern tech stack to deliver a responsive and efficient user experience.

## Getting Started

### Prerequisites

- Node.js (version as specified in `.nvmrc` if present, or latest LTS)
- npm (or yarn/pnpm/bun)

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd schedule-f-frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    # or
    # yarn install
    # or
    # pnpm install
    # or
    # bun install
    ```

### Environment Setup

1.  This project uses environment variables for configuration. You will likely need to create a `.env` file in the root directory.
2.  Copy the example environment file if one is provided (e.g., `.env.example`), or consult with the project maintainers for the required variables. Key variables may include database connection strings or API keys.
    (Refer to `drizzle.config.ts` for clues on database-related environment variables).

### Running the Development Server

To start the development server:

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

## Key Features & Architecture

This project leverages several modern web development practices and technologies:

*   **Next.js App Router**: Utilizes the Next.js App Router (`src/app/`) for server-centric routing and React Server Components, enabling optimized rendering and data fetching.
*   **Centralized State Management**: Employs `ServerDataContext.tsx` (located in `src/contexts/`) for managing table-related state, including filters, sorting, pagination, and search queries.
*   **Component-Based UI**: Features a modular component structure, with the main data table, `ServerCommentTable.tsx` (in `src/components/ServerCommentTable/`), decomposed into smaller, manageable pieces like `TableHeader.tsx`, `TableFooter.tsx`, and various field-specific components (e.g., `StringField.tsx`, `LinkField.tsx`) found in `src/components/ServerCommentTable/components/`.
*   **Text Highlighting**: Includes a `TextHighlighter.tsx` utility (in `src/components/ui/`) for highlighting text within the application.
*   **Caching Mechanism**: Implements a caching strategy using `src/lib/cache.ts`, configured by `src/lib/cache-config.ts`, to improve performance by caching frequently accessed data.
*   **Database ORM**: Uses Drizzle ORM for database interactions, with configuration in `drizzle.config.ts` and schema/migrations likely managed in the `drizzle/` directory.
*   **Testing**: Incorporates a testing environment using Jest, with configuration files (`jest.config.js`, `jest.setup.js`) and tests located in `src/__tests__/` (e.g., `CommentTable.test.tsx`).

## Project Structure

A brief overview of the key directories:

*   `src/app/`: Core application routes and pages using the Next.js App Router.
*   `src/components/`: Reusable React components.
    *   `ServerCommentTable/`: Components related to the main data table.
    *   `ui/`: General-purpose UI components like `TextHighlighter.tsx`.
*   `src/contexts/`: React context providers, including `ServerDataContext.tsx`.
*   `src/lib/`: Core application logic, utilities, and services.
    *   `actions/`: Server actions for data mutations.
    *   `db/`: Database-related utilities, seeding scripts (`seed.ts`).
    *   `hooks/`: Custom React hooks.
    *   `cache.ts`, `cache-config.ts`: Caching implementation.
*   `src/__tests__/`: Unit and integration tests.
*   `drizzle/`: Drizzle ORM configuration, schema, and migration files.
*   `public/`: Static assets (images, fonts, etc.).
*   `scripts/`: Utility scripts for tasks like warming the cache or debugging builds.

## Available Scripts

The `package.json` file defines the following scripts:

*   `npm run dev`: Starts the Next.js development server.
*   `npm run build`: Builds the application for production.
*   `npm run start`: Starts the Next.js production server (after building).
*   `npm run lint`: Lints the codebase using Next.js's ESLint configuration.
*   `npm run test`: Runs the Jest test suite.
*   `npm run test:watch`: Runs Jest in watch mode.
*   `npm run db:generate`: Generates SQL migration files using Drizzle Kit. Run this after making changes to your Drizzle schema.
*   `npm run db:migrate`: Applies pending migrations to the database using Drizzle Kit.
*   `npm run db:push`: Pushes your Drizzle schema changes directly to the database (primarily for development/prototyping; use `db:generate` and `db:migrate` for production workflows).
*   `npm run db:studio`: Opens Drizzle Studio for browsing your database.
*   `npm run db:seed`: Seeds the database using the script in `src/lib/db/seed.ts`.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

TODO: 
1. Create attribution page
2. 