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
