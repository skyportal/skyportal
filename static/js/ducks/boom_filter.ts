/**
 * Broker filter-version duck (the pipeline-filter builder at
 * `/brokers/{id}/filter/{fid}`).
 *
 * RTK Query conversion of the old `boom_filter` action/reducer duck: the ambient
 * `state.boom_filter_v` slice (read by every builder component) becomes the
 * shared `useBoomFilterVersion()` hook, which RTK Query dedupes so all consumers
 * share one request/cache entry. Endpoints target the active broker via
 * `brokerFilterBase()` (`/api/brokers/{id}`), set by the /brokers page.
 */
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
      { filter_id: any; altdata?: any; filters?: any; name?: any }
    >({
      query: ({ filter_id, altdata, filters, name }) => ({
        url: `${brokerFilterBase()}/filters/${filter_id}`,
        method: "POST",
        body: { altdata, filters, name },
      }),
    }),
  }),
});

export const {
  useGetBoomFilterVersionQuery,
  useEditBoomFilterVersionMutation,
  useUpdateBoomGroupFilterMutation,
} = boomFilterApi;

// Shared read of the current broker filter version, keyed by the :fid route
// param. Replaces the ambient `state.boom_filter_v` slice that many builder
// components read; RTK Query dedupes so they all share one request/cache entry.
export const useBoomFilterVersion = () => {
  const { fid } = useParams();
  return useGetBoomFilterVersionQuery(fid ?? "", { skip: !fid });
};
