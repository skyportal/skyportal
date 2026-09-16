/**
 * SuperObjs: groups of Objs that are one physical object. A linked moving-object
 * track is one of these, with an Obj per detection epoch, which is why the
 * scanning view reads a track rather than the individual epochs.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface SuperObjThumbnail {
  id: number;
  type: string;
  public_url: string | null;
  origin: string | null;
}

export interface SuperObjAnnotation {
  origin: string;
  data: Record<string, unknown>;
}

export interface SuperObjEpoch {
  id: string;
  ra: number | null;
  dec: number | null;
  /** Present only when the request asked for epochs. */
  created_at?: string;
  thumbnails?: SuperObjThumbnail[];
  annotations?: SuperObjAnnotation[];
}

export interface SuperObj {
  id: number;
  name: string | null;
  is_roid: boolean;
  created_at: string;
  objs: SuperObjEpoch[];
}

export interface SuperObjPage {
  superObjs: SuperObj[];
  totalMatches: number;
  pageNumber: number;
  numPerPage: number;
}

export interface SuperObjQuery {
  /** Attaches each epoch's thumbnails and annotations; a plain list omits them. */
  includeEpochs?: boolean;
  isRoid?: boolean;
  name?: string;
  objID?: string;
  pageNumber?: number;
  numPerPage?: number;
}

const queryString = (params: SuperObjQuery) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.append(key, String(value));
    }
  });
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
};

export const superObjsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSuperObjs: build.query<SuperObjPage, SuperObjQuery | void>({
      query: (params) => `api/super_objs${queryString(params || {})}`,
      providesTags: ["SuperObj"],
    }),
    getSuperObj: build.query<SuperObj, { id: number; includeEpochs?: boolean }>(
      {
        query: ({ id, includeEpochs }) =>
          `api/super_objs/${id}${queryString(
            includeEpochs === undefined ? {} : { includeEpochs },
          )}`,
        providesTags: ["SuperObj"],
      },
    ),
  }),
});

export const { useGetSuperObjsQuery, useGetSuperObjQuery } = superObjsApi;
