/**
 * Alert brokers: list configured brokers and query their alerts through the
 * generic `/api/brokers` API (dispatched server-side to the broker's provider).
 */
import { skyportalApi } from "../api/skyportalApi";

export interface Broker {
  id: number;
  name: string;
  broker_classname: string;
  active: boolean;
  capabilities: Record<string, boolean>;
  surveys: string[];
  filter_kind: string;
  altdata?: Record<string, unknown>;
}

export interface BrokerAlertQuery {
  brokerId: number;
  params: Record<string, string | number | undefined>;
}

const buildQuery = (params: BrokerAlertQuery["params"]) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") {
      search.append(k, String(v));
    }
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
};

export const brokersApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getBrokers: build.query<Broker[], void>({
      query: () => "api/brokers",
      providesTags: ["Broker"],
    }),
    getBrokerAlerts: build.query<unknown, BrokerAlertQuery>({
      query: ({ brokerId, params }) =>
        `api/brokers/${brokerId}/alerts${buildQuery(params)}`,
    }),
    getBrokerAlert: build.query<
      any,
      { brokerId: number; alertId: string | number }
    >({
      query: ({ brokerId, alertId }) =>
        `api/brokers/${brokerId}/alerts/${alertId}`,
    }),
    // Cross-match a position against a broker's reference catalogs (Gaia, PS1,
    // AllWISE, ...). Returns matched sources keyed by catalog name.
    getBrokerConeSearch: build.query<
      Record<string, any[]>,
      {
        brokerId: number;
        ra: number | string;
        dec: number | string;
        radius: number | string;
        radiusUnits?: string;
      }
    >({
      query: ({ brokerId, ra, dec, radius, radiusUnits = "arcsec" }) =>
        `api/brokers/${brokerId}/cone_search?ra=${ra}&dec=${dec}&radius=${radius}&radius_units=${radiusUnits}`,
    }),
    // Display photometry for an object: persisted DB rows merged with photometry
    // fetched on demand from the broker (never written to Postgres). Returns the
    // same point shape as GET /sources/{id}/photometry.
    getBrokerPhotometry: build.query<
      any[],
      {
        brokerId: number;
        alertId: string;
        survey?: string;
        format?: string;
        magsys?: string;
        refresh?: boolean;
      }
    >({
      query: ({ brokerId, alertId, survey, format, magsys, refresh }) => {
        const params = new URLSearchParams();
        if (survey) params.set("survey", survey);
        if (format) params.set("format", format);
        if (magsys) params.set("magsys", magsys);
        if (refresh) params.set("refresh", "true");
        const qs = params.toString();
        return `api/brokers/${brokerId}/alerts/${alertId}/photometry${
          qs ? `?${qs}` : ""
        }`;
      },
    }),
    // Preview a broker filter (params are filter_kind-specific).
    testBrokerFilter: build.query<
      unknown,
      { brokerId: number; params: Record<string, unknown> }
    >({
      query: ({ brokerId, params }) => ({
        url: `api/brokers/${brokerId}/filter/test`,
        method: "POST",
        body: params,
      }),
    }),
    // Quiet lookup of whether an object is already a saved source (a miss is
    // expected and must not raise an error notification).
    getSourceIfSaved: build.query<any, string>({
      query: (objectId) => `api/sources/${objectId}`,
      extraOptions: { suppressErrorNotification: true },
    }),
    saveBrokerAlertAsSource: build.mutation<
      { id: string },
      { brokerId: number; alertId: string; groupIds: number[] }
    >({
      query: ({ brokerId, alertId, groupIds }) => ({
        url: `api/brokers/${brokerId}/alerts/${alertId}/save`,
        method: "POST",
        body: { group_ids: groupIds },
      }),
    }),
    // Filters this broker manages (skyportal Filter rows with broker altdata).
    getBrokerFilters: build.query<
      {
        id: number;
        name: string;
        group_id: number;
        stream_id: number;
        altdata?: Record<string, unknown>;
      }[],
      number
    >({
      query: (brokerId) => `api/brokers/${brokerId}/filters`,
      providesTags: ["Broker"],
    }),
    // Registered provider classes + their config form schemas / capabilities.
    getBrokerAPIs: build.query<
      Record<
        string,
        {
          methodsImplemented: Record<string, boolean>;
          formSchemaConfig?: Record<string, unknown> | null;
          uiSchema?: Record<string, unknown> | null;
          surveys?: string[];
          filterKind?: string;
        }
      >,
      void
    >({
      query: () => "api/internal/broker_apis",
    }),
    createBroker: build.mutation<
      { id: number },
      {
        name: string;
        broker_classname: string;
        altdata: Record<string, unknown>;
        active?: boolean;
      }
    >({
      query: (body) => ({ url: "api/brokers", method: "POST", body }),
      invalidatesTags: ["Broker"],
    }),
    updateBroker: build.mutation<
      void,
      { id: number; patch: Record<string, unknown> }
    >({
      query: ({ id, patch }) => ({
        url: `api/brokers/${id}`,
        method: "PATCH",
        body: patch,
      }),
      invalidatesTags: ["Broker"],
    }),
    deleteBroker: build.mutation<void, number>({
      query: (id) => ({ url: `api/brokers/${id}`, method: "DELETE" }),
      invalidatesTags: ["Broker"],
    }),
  }),
});

export const {
  useGetBrokersQuery,
  useGetBrokerAlertsQuery,
  useLazyGetBrokerAlertsQuery,
  useGetBrokerAlertQuery,
  useGetBrokerPhotometryQuery,
  useLazyGetBrokerConeSearchQuery,
  useGetSourceIfSavedQuery,
  useSaveBrokerAlertAsSourceMutation,
  useLazyTestBrokerFilterQuery,
  useGetBrokerFiltersQuery,
  useGetBrokerAPIsQuery,
  useCreateBrokerMutation,
  useUpdateBrokerMutation,
  useDeleteBrokerMutation,
} = brokersApi;
