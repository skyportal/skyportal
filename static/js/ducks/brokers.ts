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
  }),
});

export const {
  useGetBrokersQuery,
  useGetBrokerAlertsQuery,
  useLazyGetBrokerAlertsQuery,
  useGetBrokerAlertQuery,
  useGetSourceIfSavedQuery,
  useSaveBrokerAlertAsSourceMutation,
  useLazyTestBrokerFilterQuery,
} = brokersApi;
