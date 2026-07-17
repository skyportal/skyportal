import { skyportalApi } from "../api/skyportalApi";

export interface AlertArg {
  survey: string;
  id: string | number;
}

export interface SaveAlertArg {
  survey: string;
  id: string | number;
  payload: Record<string, any>;
}

// One BOOM object's alerts + object record + "save as source". RTK Query
// conversion of the old boom_alert thunks; the per-object keyed slices
// (boom_alert_data / boom_object_data) are replaced by RTK's per-arg cache, so
// consumers read the query hook's `data` for the current objectId.
export const boomAlertApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAlertData: build.query<any, AlertArg>({
      query: ({ survey, id }) =>
        `api/boom/surveys/${survey}/alerts?objectId=${id}`,
    }),
    getBoomObject: build.query<any, AlertArg>({
      query: ({ survey, id }) => `api/boom/surveys/${survey}/objects/${id}`,
    }),
    saveAlertAsSource: build.mutation<any, SaveAlertArg>({
      query: ({ survey, id, payload }) => ({
        url: `api/boom/surveys/${survey}/objects/${id}`,
        method: "POST",
        body: payload,
      }),
    }),
  }),
});

export const {
  useGetAlertDataQuery,
  useLazyGetAlertDataQuery,
  useGetBoomObjectQuery,
  useLazyGetBoomObjectQuery,
  useSaveAlertAsSourceMutation,
} = boomAlertApi;
