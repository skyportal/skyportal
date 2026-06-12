/**
 * Bridges baselayer's websocket `MessageHandler` to RTK Query cache
 * invalidation.
 *
 * The old ducks registered a `messageHandler.add(...)` callback per duck that,
 * on a given `REFRESH_*` actionType, conditionally re-dispatched a fetch thunk
 * (often gated on store state, e.g. "only refresh if the currently-loaded
 * source matches the pushed obj_key"). The RTK Query equivalent is to invalidate
 * the relevant tag(s): only *active* queries for those tags refetch.
 *
 * `invalidateOnMessage` preserves the conditional logic: `getTags` receives the
 * websocket payload and a `getState` accessor and returns the tags to
 * invalidate, or `null`/`[]` to ignore the message.
 */
import messageHandler from "baselayer/MessageHandler";

import { skyportalApi } from "./skyportalApi";

type ApiTag = Parameters<typeof skyportalApi.util.invalidateTags>[0][number];

/**
 * Register a websocket-driven tag invalidation.
 *
 * @param actionType  the websocket message `actionType` to react to
 *                    (e.g. "skyportal/REFRESH_SOURCE").
 * @param getTags     maps the message payload (+ a `getState` accessor) to the
 *                    tags to invalidate; return `null` to ignore this message.
 */
export function invalidateOnMessage(
  actionType: string,
  getTags: (
    payload: any,
    getState: () => unknown,
  ) => ApiTag[] | null | undefined,
): void {
  messageHandler.add(
    (
      incomingType: string,
      payload: any,
      dispatch: (action: unknown) => unknown,
      getState: () => unknown,
    ) => {
      if (incomingType !== actionType) {
        return;
      }
      const tags = getTags(payload, getState);
      if (tags && tags.length > 0) {
        dispatch(skyportalApi.util.invalidateTags(tags));
      }
    },
  );
}

/**
 * Look up the argument a cached query was fetched with, by matching on its
 * result data.
 *
 * SkyPortal's websocket `REFRESH_*` payloads identify a source by its
 * `internal_key` (a hash), whereas the RTK Query cache for `getSource` is keyed
 * by the obj id (`api/sources/{id}`). To invalidate a single source's cache
 * entry from a websocket message we translate `internal_key` -> obj id by
 * finding the cached `getSource` result whose `internal_key` matches and
 * returning the argument it was fetched with.
 *
 * Returns `null` when no matching cached query is found (e.g. that source isn't
 * currently loaded), so callers can fall back to a broad invalidation.
 */
export function findCachedQueryArg(
  getState: () => unknown,
  endpointName: string,
  match: (data: any) => boolean,
): unknown {
  const queries = (getState() as any)?.skyportalApi?.queries ?? {};
  for (const entry of Object.values(queries) as any[]) {
    if (entry?.endpointName === endpointName && match(entry?.data)) {
      return entry.originalArgs;
    }
  }
  return null;
}
