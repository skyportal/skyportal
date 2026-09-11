import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage, findCachedQueryArg } from "../api/wsInvalidation";
import { dataAvailabilityTag } from "./dataAvailabilityTags";
import { sourceTag } from "./sourceTags";

export interface DataOwner {
  id: number;
  username: string;
  first_name: string | null;
  last_name: string | null;
}

export interface DataRequestStub {
  id: number;
  status: "pending" | "accepted" | "declined";
}

/** One owner's photometry on a source, in a single instrument and filter. */
export interface PhotometryAvailability {
  owner: DataOwner | null;
  instrument: { id: number; name: string } | null;
  filter: string;
  num_points: number;
  first_mjd: number | null;
  last_mjd: number | null;
  request: DataRequestStub | null;
}

export interface SpectrumAvailability {
  id: number;
  owner: DataOwner | null;
  instrument: { id: number; name: string } | null;
  observed_at: string | null;
  observed_at_mjd: number | null;
  type: string | null;
  label: string | null;
  origin: string | null;
  request: DataRequestStub | null;
}

export interface DataAvailability {
  photometry: PhotometryAvailability[];
  spectra: SpectrumAvailability[];
}

export interface DataAccessRequest {
  id: number;
  status: "pending" | "accepted" | "declined";
  message: string | null;
  obj_id: string;
  data_type: "photometry" | "spectrum";
  instrument_id: number | null;
  filter: string | null;
  spectrum_id: number | null;
  granted_group_id: number | null;
  created_at: string;
  requester: DataOwner;
  owner: DataOwner;
  /** Groups both the requester and the viewer belong to. */
  shareable_groups: { id: number; name: string }[];
}

export interface DataAccessRequestPage {
  requests: DataAccessRequest[];
  totalMatches: number;
  pageNumber: number;
  numPerPage: number;
}

export interface PhotometryDatasetRef {
  ownerID: number;
  instrumentID: number;
  filter: string;
}

export const dataAccessRequestsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDataAvailability: build.query<DataAvailability, string>({
      query: (obj_id) => `api/sources/${obj_id}/data_availability`,
      providesTags: (_result, _error, obj_id) => dataAvailabilityTag(obj_id),
    }),
    getDataAccessRequests: build.query<
      DataAccessRequestPage,
      {
        direction?: "incoming" | "outgoing";
        status?: string;
        pageNumber?: number;
        numPerPage?: number;
      } | void
    >({
      query: (params) => ({
        url: "api/data_access_request",
        params: (params ?? {}) as Record<string, string>,
      }),
      providesTags: ["DataAccessRequest"],
    }),
    requestDataAccess: build.mutation<
      { ids: number[] },
      {
        objId: string;
        photometry?: PhotometryDatasetRef[];
        spectrumIDs?: number[];
        message?: string | null;
      }
    >({
      query: (body) => ({
        url: "api/data_access_request",
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { objId }) => [
        ...dataAvailabilityTag(objId),
        "DataAccessRequest",
        ...sourceTag(objId),
      ],
    }),
    answerDataAccessRequest: build.mutation<
      unknown,
      { id: number; status: "accepted" | "declined"; groupID?: number | null }
    >({
      query: ({ id, ...body }) => ({
        url: `api/data_access_request/${id}`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: ["DataAccessRequest", "DataAvailability"],
    }),
    withdrawDataAccessRequest: build.mutation<unknown, number>({
      query: (id) => ({
        url: `api/data_access_request/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["DataAccessRequest", "DataAvailability"],
    }),
  }),
});

// The owner answering a request is a different session from the requester's, so
// the requester's list is refreshed by its own push.
invalidateOnMessage("skyportal/REFRESH_DATA_ACCESS_REQUESTS", () => [
  "DataAccessRequest",
]);

// A grant lands as new photometry/spectra on the source the requester is
// looking at. REFRESH_SOURCE is broadcast to every client for every source, and
// carries the source's internal_key, so translate that to the obj id and
// refresh only that source's availability. Without an obj id there is nothing
// to refresh: an unscoped tag here matches every open source page.
invalidateOnMessage("skyportal/REFRESH_SOURCE", (payload, getState) => {
  const objKey = payload?.obj_key as string | undefined;
  if (!objKey) {
    return null;
  }
  const objId = findCachedQueryArg(
    getState,
    "getSource",
    (data) => data?.internal_key === objKey,
  ) as string | null;
  return objId != null ? dataAvailabilityTag(objId) : null;
});

export const {
  useGetDataAvailabilityQuery,
  useGetDataAccessRequestsQuery,
  useRequestDataAccessMutation,
  useAnswerDataAccessRequestMutation,
  useWithdrawDataAccessRequestMutation,
} = dataAccessRequestsApi;
