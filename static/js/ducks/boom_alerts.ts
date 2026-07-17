import { skyportalApi } from "../api/skyportalApi";

export interface FetchAlertsArg {
  survey: string;
  object_id?: string | undefined;
  ra?: number | string | undefined;
  dec?: number | string | undefined;
  radius?: number | string | undefined;
}

// Alerts for a BOOM survey, by objectId and/or cone (ra/dec/radius). RTK Query
// conversion of the old `fetchAlerts` thunk + "alerts" slice; the component now
// reads `data`/`isFetching` from the (lazy) query hook instead of the slice.
export const boomAlertsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAlerts: build.query<any, FetchAlertsArg>({
      query: ({ survey, object_id, ra, dec, radius }) => {
        const params = new URLSearchParams();
        if (object_id) {
          params.set("objectId", object_id);
        }
        if (ra && dec && radius) {
          params.set("ra", String(ra));
          params.set("dec", String(dec));
          params.set("radius", String(radius));
          params.set("radius_units", "arcsec");
        }
        const qs = params.toString();
        return qs
          ? `api/boom/surveys/${survey}/alerts?${qs}`
          : `api/boom/surveys/${survey}/alerts`;
      },
    }),
  }),
});

export const { useGetAlertsQuery, useLazyGetAlertsQuery } = boomAlertsApi;
