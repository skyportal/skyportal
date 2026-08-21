/**
 * RTK Query adapter for the first-party `skyportal-js` client.
 *
 * Converted ducks express their endpoints as calls to the client's typed
 * endpoint functions (via `queryFn`) instead of hand-building URLs and body
 * shapes. The client unwraps the `{status,data,message}` envelope itself and
 * throws on application errors; `clientQuery` maps that to the same
 * CUSTOM_ERROR shape and error notification as `skyportalBaseQuery`, so
 * converted and unconverted endpoints behave identically to consumers.
 *
 * Auth rides on the session cookie: requests stay same-origin and the client
 * adds no Authorization header when created without a token.
 */
import type { BaseQueryApi, FetchBaseQueryError } from "@reduxjs/toolkit/query";

import { showNotification } from "baselayer/components/Notifications";

import type { SkyPortal } from "skyportal-js/Client";
import { createClient } from "skyportal-js/Client";

/**
 * Build a client whose requests abort with RTK Query's per-call signal (fired
 * when a query is superseded or unsubscribed). The client's own timeout is
 * disabled to match the old fetch-based behaviour, which had none.
 */
const makeClient = (signal: AbortSignal): SkyPortal =>
  createClient(window.location.origin, {
    timeout: null,
    fetch: (input, init) => fetch(input, { ...init, signal }),
  });

interface ClientQueryOptions {
  /** Skip the error notification, for endpoints that expect misses. */
  suppressErrorNotification?: boolean;
}

/**
 * Run one skyportal-js call as an RTK Query `queryFn` body.
 *
 *   queryFn: (arg, api) => clientQuery(api, (client) => client.fetchAcls()),
 */
export const clientQuery = async <T>(
  api: BaseQueryApi,
  run: (client: SkyPortal) => Promise<T>,
  options: ClientQueryOptions = {},
): Promise<{ data: T } | { error: FetchBaseQueryError }> => {
  try {
    return { data: await run(makeClient(api.signal)) };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    // An abort is RTK Query housekeeping, not a user-facing failure.
    if (!api.signal.aborted && !options.suppressErrorNotification) {
      api.dispatch(showNotification(`${message}`, "error"));
    }
    return {
      error: {
        status: "CUSTOM_ERROR",
        error: message,
        data: { status: "error", message },
      } satisfies FetchBaseQueryError,
    };
  }
};
