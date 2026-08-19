/**
 * News feed widget data.
 *
 * RTK Query conversion of the old `FETCH_NEWSFEED` duck. The backend returns an
 * array of news feed items; the old slice stored them under `items`, so the
 * query result is the array itself and consumers read it directly.
 *
 * The old websocket handler refetched the news feed on a FETCH_NEWSFEED
 * message; here we invalidate the "NewsFeed" tag so the active query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type NewsFeedItem = Record<string, any>;

export const newsFeedApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // Optional `teamID` scopes the feed to a single team's groups.
    getNewsFeed: build.query<NewsFeedItem[], { teamID?: number | null } | void>(
      {
        queryFn: (arg, api) =>
          clientQuery(api, (client) =>
            client.fetchNewsFeed(
              arg && arg.teamID != null ? { teamId: arg.teamID } : {},
            ),
          ),
        providesTags: ["NewsFeed"],
      },
    ),
  }),
});

// Websocket: old handler refetched the news feed on FETCH_NEWSFEED.
invalidateOnMessage("skyportal/FETCH_NEWSFEED", () => ["NewsFeed"]);

export const { useGetNewsFeedQuery } = newsFeedApi;
