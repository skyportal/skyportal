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
import { clientQuery } from "../api/skyportalClient";
import { brokerFilterTargetId } from "./brokerFilterTarget";

export const boomFilterApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getBoomFilterVersion: build.query<any, string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.fetchBrokerFilter(brokerFilterTargetId(), Number(id)),
        ),
    }),
    editBoomFilterVersion: build.mutation<
      any,
      { filter_id: any; active: any; active_fid: any }
    >({
      queryFn: ({ filter_id, active, active_fid }, api) =>
        clientQuery(api, (client) =>
          client.updateBrokerFilter(brokerFilterTargetId(), Number(filter_id), {
            active,
            activeFid: active_fid,
          }),
        ),
    }),
    updateBoomGroupFilter: build.mutation<
      any,
      // `name` is not sent: the handler names the version after the skyportal
      // Filter row it is attached to.
      { filter_id: any; altdata?: any; filters?: any }
    >({
      queryFn: ({ filter_id, altdata, filters }, api) =>
        clientQuery(api, (client) =>
          client.postBrokerFilter(brokerFilterTargetId(), Number(filter_id), {
            altdata,
            filters,
          }),
        ),
    }),
    // Slow: runs the filter over a night of alerts on the broker. Records the
    // verdict server-side (keyed on fid) so the version can then be activated.
    validateBoomFilter: build.mutation<any, { filter_id: any; fid?: any }>({
      queryFn: ({ filter_id, fid }, api) =>
        clientQuery(api, (client) =>
          client.postBrokerFilterValidation(
            brokerFilterTargetId(),
            Number(filter_id),
            fid ? { fid } : {},
          ),
        ),
    }),
  }),
});

export const {
  useGetBoomFilterVersionQuery,
  useEditBoomFilterVersionMutation,
  useUpdateBoomGroupFilterMutation,
  useValidateBoomFilterMutation,
} = boomFilterApi;

// Shared read of the current broker filter version, keyed by the :fid route
// param. Replaces the ambient `state.boom_filter_v` slice that many builder
// components read; RTK Query dedupes so they all share one request/cache entry.
export const useBoomFilterVersion = () => {
  const { fid } = useParams();
  return useGetBoomFilterVersionQuery(fid ?? "", { skip: !fid });
};
