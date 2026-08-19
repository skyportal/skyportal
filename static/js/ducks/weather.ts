/**
 * Weather widget data.
 *
 * RTK Query conversion of the old `FETCH_WEATHER` duck. The optional
 * `telescope_id` arg selects the telescope to report weather for. The old
 * websocket handler refetched weather on a FETCH_WEATHER message; here we
 * invalidate the "Weather" tag so the active query (whatever telescope) refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type Weather = Record<string, any>;

export const weatherApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getWeather: build.query<Weather, number | string | null | void>({
      queryFn: (telescope_id, api) =>
        clientQuery(api, (client) =>
          client.fetchWeather(
            telescope_id ? { telescopeId: Number(telescope_id) } : {},
          ),
        ),
      providesTags: ["Weather"],
    }),
  }),
});

// Websocket: old handler refetched weather on FETCH_WEATHER.
invalidateOnMessage("skyportal/FETCH_WEATHER", () => ["Weather"]);

export const { useGetWeatherQuery } = weatherApi;
