/**
 * Alert brokers: list configured brokers and query their alerts through the
 * generic `/api/brokers` API (dispatched server-side to the broker's provider).
 */
import { buildQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";

export interface Broker {
  id: number;
  name: string;
  broker_classname: string;
  active: boolean;
  default_alert_search: boolean;
  default_crossmatch: boolean;
  default_photometry: boolean;
  capabilities: Record<string, boolean>;
  surveys: string[];
  filter_kind: string;
  altdata?: Record<string, unknown>;
}

export interface BrokerCredential {
  id: number;
  broker_id: number;
  topics: string[];
  topic_filter_ids: Record<string, number[]>;
  /** Non-secret values only; secrets are reported by name in secrets_set. */
  credentials: Record<string, unknown>;
  secrets_set: string[];
}

export interface BrokerCredentialPatch {
  credentials?: Record<string, unknown>;
  /** Overwrite all stored credentials rather than merging the fields sent. */
  replace_credentials?: boolean;
  topics?: string[];
  topic_filter_ids?: Record<string, number[]>;
}

export interface BrokerAlertQuery {
  brokerId: number;
  params: Record<string, string | number | undefined>;
}

export interface BrokerFilter {
  id: number;
  name: string;
  group_id: number;
  stream_id: number;
  broker_id: number | null;
  altdata?: Record<string, unknown>;
}

export interface FilterCatalogQuery {
  pageNumber?: number | undefined;
  numPerPage?: number | undefined;
  name?: string | undefined;
  groupID?: number | "" | undefined;
  streamID?: number | "" | undefined;
  brokerID?: number | "" | "none" | undefined;
}

const DEFAULT_FIELDS = [
  "default_alert_search",
  "default_crossmatch",
  "default_photometry",
] as const;

const buildQuery = (params: Record<string, string | number | undefined>) => {
  const qs = buildQueryString(params);
  return qs ? `?${qs}` : "";
};

// 64-bit alert ids: JSON.parse would round them, so keep them as strings.
const ID_KEYS = /"(candid|_id|diaSourceId|diaObjectId)":\s*(\d{16,})/g;
const parseKeepingIds = async (response: Response) => {
  const text = await response.text();
  return JSON.parse(text.replace(ID_KEYS, '"$1":"$2"'));
};

export const brokersApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getBrokers: build.query<Broker[], void>({
      query: () => "api/brokers",
      providesTags: ["Broker"],
    }),
    getBrokerAlerts: build.query<unknown, BrokerAlertQuery>({
      query: ({ brokerId, params }) => ({
        url: `api/brokers/${brokerId}/alerts${buildQuery(params)}`,
        responseHandler: parseKeepingIds,
      }),
    }),
    getBrokerAlert: build.query<
      any,
      { brokerId: number; alertId: string | number }
    >({
      query: ({ brokerId, alertId }) => ({
        url: `api/brokers/${brokerId}/alerts/${alertId}`,
        responseHandler: parseKeepingIds,
      }),
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
    // Preview a broker filter (params are filter_kind-specific).
    testBrokerFilter: build.query<
      unknown,
      { brokerId: number; params: Record<string, unknown> }
    >({
      query: ({ brokerId, params }) => ({
        url: `api/brokers/${brokerId}/filter/test`,
        method: "POST",
        body: params,
        responseHandler: parseKeepingIds,
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
    getBrokerFilters: build.query<BrokerFilter[], number>({
      query: (brokerId) => `api/brokers/${brokerId}/filters`,
      providesTags: ["Broker"],
    }),
    // Every filter with its broker, and the binding that attaches one.
    getFilterCatalog: build.query<
      { filters: BrokerFilter[]; totalMatches: number },
      FilterCatalogQuery
    >({
      query: (params) => `api/brokers/filters${buildQuery({ ...params })}`,
      providesTags: ["Broker"],
    }),
    attachFilterToBroker: build.mutation<
      { id: number; broker_id: number },
      { filterId: number; brokerId: number }
    >({
      query: ({ filterId, brokerId }) => ({
        url: `api/brokers/filters/${filterId}/attach`,
        method: "POST",
        body: { broker_id: brokerId },
      }),
      invalidatesTags: ["Broker"],
    }),
    // Save a query-kind broker filter (Lasair): stores selected/tables/conditions
    // on the skyportal Filter's altdata.
    saveBrokerFilter: build.mutation<
      { id: number; altdata?: Record<string, unknown> },
      {
        brokerId: number;
        filterId: number;
        query: { selected: string; tables: string; conditions: string };
        autosave?: boolean;
      }
    >({
      query: ({ brokerId, filterId, query, autosave }) => ({
        url: `api/brokers/${brokerId}/filters/${filterId}`,
        method: "POST",
        body: { query, autosave },
      }),
      invalidatesTags: ["Broker"],
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
      async onQueryStarted({ id, patch }, { dispatch, queryFulfilled }) {
        const rollback = dispatch(
          brokersApi.util.updateQueryData("getBrokers", undefined, (draft) => {
            draft.forEach((broker) => {
              if (broker.id === id) {
                Object.assign(broker, patch);
              } else {
                DEFAULT_FIELDS.forEach((field) => {
                  if (patch[field]) broker[field] = false;
                });
              }
            });
          }),
        );
        try {
          await queryFulfilled;
        } catch {
          rollback.undo();
        }
      },
      invalidatesTags: ["Broker"],
    }),
    getBrokerCredentials: build.query<BrokerCredential | null, number>({
      query: (id) => `api/brokers/${id}/credentials`,
      providesTags: ["BrokerCredential"],
    }),
    getBrokerCredentialTopics: build.query<{ topics: string[] }, number>({
      query: (id) => `api/brokers/${id}/credentials/topics`,
      providesTags: ["BrokerCredential"],
    }),
    setBrokerCredentials: build.mutation<
      { id: number },
      { brokerId: number; patch: BrokerCredentialPatch }
    >({
      query: ({ brokerId, patch }) => ({
        url: `api/brokers/${brokerId}/credentials`,
        method: "PUT",
        body: patch,
      }),
      invalidatesTags: ["BrokerCredential"],
    }),
    deleteBrokerCredentials: build.mutation<void, number>({
      query: (id) => ({
        url: `api/brokers/${id}/credentials`,
        method: "DELETE",
      }),
      invalidatesTags: ["BrokerCredential"],
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
  useLazyGetBrokerConeSearchQuery,
  useGetSourceIfSavedQuery,
  useSaveBrokerAlertAsSourceMutation,
  useLazyTestBrokerFilterQuery,
  useGetBrokerFiltersQuery,
  useGetFilterCatalogQuery,
  useAttachFilterToBrokerMutation,
  useSaveBrokerFilterMutation,
  useGetBrokerAPIsQuery,
  useCreateBrokerMutation,
  useUpdateBrokerMutation,
  useDeleteBrokerMutation,
  useGetBrokerCredentialsQuery,
  useLazyGetBrokerCredentialTopicsQuery,
  useSetBrokerCredentialsMutation,
  useDeleteBrokerCredentialsMutation,
} = brokersApi;
