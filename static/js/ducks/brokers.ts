/**
 * Alert brokers: list configured brokers and query their alerts through the
 * generic `/api/brokers` API (dispatched server-side to the broker's provider).
 */
import type {
  Broker,
  BrokerFilter,
  BrokerFilterAttachResponse,
  BrokerFilterPostResponse,
  BrokerPost,
} from "skyportal-js/Brokers";

import { buildQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

export type { Broker, BrokerFilter } from "skyportal-js/Brokers";

export interface BrokerAlertQuery {
  brokerId: number;
  params: Record<string, string | number | undefined>;
}

export interface FilterCatalogQuery {
  pageNumber?: number | undefined;
  numPerPage?: number | undefined;
  name?: string | undefined;
  groupID?: number | "" | undefined;
  streamID?: number | "" | undefined;
  brokerID?: number | "" | "none" | undefined;
}

/** The broker fields the list page edits, in the API's snake_case. */
interface BrokerPatch {
  name?: string;
  active?: boolean;
  altdata?: Record<string, unknown>;
  default_alert_search?: boolean;
  default_crossmatch?: boolean;
}

const DEFAULT_FIELDS = ["default_alert_search", "default_crossmatch"] as const;

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
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchBrokers()),
      providesTags: ["Broker"],
    }),
    // raw: alert payloads carry 64-bit ids that must survive JSON parsing, so
    // they need the custom responseHandler below; the client parses with
    // response.json().
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
      Record<string, unknown>,
      {
        brokerId: number;
        ra: number | string;
        dec: number | string;
        radius: number | string;
        radiusUnits?: string;
      }
    >({
      queryFn: ({ brokerId, ra, dec, radius, radiusUnits = "arcsec" }, api) =>
        clientQuery(api, (client) =>
          client.fetchBrokerConeSearch(
            brokerId,
            Number(ra),
            Number(dec),
            Number(radius),
            { radiusUnits },
          ),
        ),
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
      queryFn: ({ brokerId, alertId, survey, format, magsys, refresh }, api) =>
        clientQuery(api, (client) =>
          client.fetchBrokerPhotometry(brokerId, alertId, {
            survey,
            format,
            magsys,
            refresh,
          }),
        ),
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
      queryFn: (objectId, api) =>
        clientQuery(api, (client) => client.fetchSource(objectId), {
          suppressErrorNotification: true,
        }),
    }),
    saveBrokerAlertAsSource: build.mutation<
      { id: string },
      { brokerId: number; alertId: string; groupIds: number[] }
    >({
      queryFn: ({ brokerId, alertId, groupIds }, api) =>
        clientQuery(api, (client) =>
          client.postBrokerAlertSave(brokerId, alertId, groupIds),
        ),
    }),
    // Filters this broker manages (skyportal Filter rows with broker altdata).
    getBrokerFilters: build.query<BrokerFilter[], number>({
      queryFn: (brokerId, api) =>
        clientQuery(api, (client) => client.fetchBrokerFilters(brokerId)),
      providesTags: ["Broker"],
    }),
    // Every filter with its broker, and the binding that attaches one.
    getFilterCatalog: build.query<
      { filters: BrokerFilter[]; totalMatches: number },
      FilterCatalogQuery
    >({
      queryFn: (
        { pageNumber, numPerPage, name, groupID, streamID, brokerID },
        api,
      ) =>
        clientQuery(api, (client) =>
          client.fetchBrokerFilterCatalog({
            pageNumber,
            numPerPage,
            name,
            groupId: groupID === "" ? undefined : groupID,
            streamId: streamID === "" ? undefined : streamID,
            brokerId: brokerID === "" ? undefined : brokerID,
          }),
        ),
      providesTags: ["Broker"],
    }),
    attachFilterToBroker: build.mutation<
      BrokerFilterAttachResponse,
      { filterId: number; brokerId: number }
    >({
      queryFn: ({ filterId, brokerId }, api) =>
        clientQuery(api, (client) =>
          client.postBrokerFilterAttach(filterId, brokerId),
        ),
      invalidatesTags: ["Broker"],
    }),
    // Save a query-kind broker filter (Lasair): stores selected/tables/conditions
    // on the skyportal Filter's altdata.
    saveBrokerFilter: build.mutation<
      BrokerFilterPostResponse,
      {
        brokerId: number;
        filterId: number;
        query: { selected: string; tables: string; conditions: string };
        autosave?: boolean;
      }
    >({
      queryFn: ({ brokerId, filterId, query, autosave }, api) =>
        clientQuery(api, (client) =>
          client.postBrokerFilter(brokerId, filterId, { query, autosave }),
        ),
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
    createBroker: build.mutation<{ id: number }, BrokerPost>({
      queryFn: (body, api) =>
        clientQuery(api, (client) => client.postBroker(body)),
      invalidatesTags: ["Broker"],
    }),
    updateBroker: build.mutation<void, { id: number; patch: BrokerPatch }>({
      queryFn: ({ id, patch }, api) =>
        clientQuery(api, (client) =>
          client.updateBroker(id, {
            name: patch.name,
            active: patch.active,
            altdata: patch.altdata,
            defaultAlertSearch: patch.default_alert_search,
            defaultCrossmatch: patch.default_crossmatch,
          }),
        ),
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
    deleteBroker: build.mutation<void, number>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteBroker(id)),
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
  useGetFilterCatalogQuery,
  useAttachFilterToBrokerMutation,
  useSaveBrokerFilterMutation,
  useGetBrokerAPIsQuery,
  useCreateBrokerMutation,
  useUpdateBrokerMutation,
  useDeleteBrokerMutation,
} = brokersApi;
