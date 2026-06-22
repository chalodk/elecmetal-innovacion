import { QueryClient } from "@tanstack/react-query";

function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30 * 1000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

/** Factory — safe for server components (creates a fresh client each time). */
export function makeQueryClient(): QueryClient {
  return createQueryClient();
}

let browserQueryClient: QueryClient | undefined;

/** Singleton getter — for client components (reuses the same instance). */
export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    // Server: always make a new one
    return createQueryClient();
  }
  if (!browserQueryClient) {
    browserQueryClient = createQueryClient();
  }
  return browserQueryClient;
}
