/**
 * Weather widget data.
 *
 * RTK Query conversion of the old `FETCH_WEATHER` duck. The optional
 * `telescope_id` arg selects the telescope to report weather for.
 */
import { skyportalApi } from "../api/skyportalApi";

export type Weather = Record<string, any>;

export const weatherApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getWeather: build.query<Weather, number | string | null | void>({
      query: (telescope_id) =>
        telescope_id
          ? `api/weather?telescope_id=${telescope_id}`
          : "api/weather",
      providesTags: ["Weather"],
    }),
  }),
});

export const { useGetWeatherQuery } = weatherApi;
