import { useParams } from "react-router-dom";
import { skyportalApi } from "../api/skyportalApi";

// Only fetch/edit/update are used by the app; the legacy duck's other action
// creators (addGroupFilter, editAutosave, ...) had no consumers and were dropped.
export const boomFilterApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getBoomFilterVersion: build.query<any, string>({
      query: (id) => `api/boom/filters/${id}`,
    }),
    editBoomFilterVersion: build.mutation<
      any,
      { filter_id: any; active: any; active_fid: any }
    >({
      query: ({ filter_id, active, active_fid }) => ({
        url: `api/boom/filters/${filter_id}`,
        method: "PATCH",
        body: { active, active_fid },
      }),
    }),
    updateBoomGroupFilter: build.mutation<
      any,
      { filter_id: any; altdata?: any; filters?: any; name?: any }
    >({
      query: ({ filter_id, altdata, filters, name }) => ({
        url: `api/boom/filters/${filter_id}`,
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

// Shared read of the current boom filter version, keyed by the :fid route param.
// Replaces the ambient `state.boom_filter_v` slice that many builder components
// read; RTK Query dedupes so they all share one request/cache entry.
export const useBoomFilterVersion = () => {
  const { fid } = useParams();
  return useGetBoomFilterVersionQuery(fid ?? "", { skip: !fid });
};
