import { useParams } from "react-router-dom";

import { skyportalApi } from "../api/skyportalApi";
import { brokerFilterBase } from "./brokerFilterTarget";

export const boomFilterApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getBoomFilterVersion: build.query<any, string>({
      query: (id) => `${brokerFilterBase()}/filters/${id}`,
    }),
    editBoomFilterVersion: build.mutation<
      any,
      { filter_id: any; active: any; active_fid: any }
    >({
      query: ({ filter_id, active, active_fid }) => ({
        url: `${brokerFilterBase()}/filters/${filter_id}`,
        method: "PATCH",
        body: { active, active_fid },
      }),
    }),
    updateBoomGroupFilter: build.mutation<
      any,
      {
        filter_id: any;
        altdata?: any;
        filters?: any;
        name?: any;
        watchlist?: string | null;
      }
    >({
      query: ({ filter_id, altdata, filters, name, watchlist }) => ({
        url: `${brokerFilterBase()}/filters/${filter_id}`,
        method: "POST",
        body: { altdata, filters, name, ...(watchlist ? { watchlist } : {}) },
      }),
    }),
    // Keyed by the broker base URL, so switching brokers refetches.
    getBrokerWatchlists: build.query<string[], string>({
      query: (base) => `${base}/watchlists`,
    }),
    updateBoomFilterFlags: build.mutation<
      any,
      {
        filter_id: any;
        autoSave?: boolean;
        autoAnnotate?: boolean;
        autoFollowup?: boolean;
        autoSaveIgnoreGroupIds?: number[];
        autoSaveIgnoreRadius?: number | null;
        autoSaveSaverId?: number | null;
        autoSaveComment?: string | null;
        autoFollowupDefaultId?: number | null;
      }
    >({
      query: ({ filter_id, ...flags }) => ({
        url: `${brokerFilterBase()}/filters/${filter_id}`,
        method: "PATCH",
        body: flags,
      }),
    }),
    // Returns at once: the verdict stays pending on the filter until the replay ends.
    validateBoomFilter: build.mutation<any, { filter_id: any; fid?: any }>({
      query: ({ filter_id, fid }) => ({
        url: `${brokerFilterBase()}/filters/${filter_id}/validate`,
        method: "POST",
        body: fid ? { fid } : {},
      }),
    }),
  }),
});

export const {
  useGetBoomFilterVersionQuery,
  useGetBrokerWatchlistsQuery,
  useEditBoomFilterVersionMutation,
  useUpdateBoomGroupFilterMutation,
  useUpdateBoomFilterFlagsMutation,
  useValidateBoomFilterMutation,
} = boomFilterApi;

export const useBoomFilterVersion = (
  options: { pollingInterval?: number } = {},
) => {
  const { fid } = useParams();
  return useGetBoomFilterVersionQuery(fid ?? "", { skip: !fid, ...options });
};
