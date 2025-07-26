# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

- `npm run dev` - Start development server with HMR at http://localhost:5173
- `npm run build` - Create production build (outputs to `build/` directory)
- `npm run start` - Start production server from build
- `npm run typecheck` - Run TypeScript type checking and React Router type generation

## Architecture Overview

This is a React Router v7 application with the following structure:

### Core Framework
- **React Router v7** - Full-stack React framework with SSR enabled by default
- **Vite** - Build tool and development server
- **TypeScript** - Strict mode enabled with ES2022 target
- **TailwindCSS** - Styling framework with v4 and shadcn/ui integration

### Project Structure
- `app/` - Main application code
  - `root.tsx` - Root layout component with error boundary
  - `routes.ts` - Route configuration (currently single index route)
  - `routes/` - Route components
  - `components/` - Reusable components (shadcn/ui structure)
  - `lib/` - Utility functions
- `react-router.config.ts` - React Router configuration (SSR enabled)
- `vite.config.ts` - Vite configuration with TailwindCSS and tsconfigPaths plugins

### Application Context
The app appears to be an "Instagram Bot Dashboard" based on the index route content, with data structures for managing Instagram accounts including:
- Username tracking
- AdsPower integration IDs
- Account status management (Suspended/Authenticated/Unauthenticated/Appealed)

### Key Configuration
- TypeScript path mapping: `~/*` maps to `./app/*`
- Shadcn/ui configured with "new-york" style and Lucide icons
- CSS variables enabled for theming
- React Router type generation integrated with TypeScript

### Build Output
Production builds create:
- `build/client/` - Static assets
- `build/server/` - Server-side code

## Deployment
The application includes Docker support and can be deployed to various platforms including AWS ECS, Google Cloud Run, Azure Container Apps, Digital Ocean, Fly.io, and Railway.