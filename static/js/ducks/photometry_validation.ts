/**
 * Photometry validation.
 *
 * RTK Query conversion of the old `SUBMIT/DELETE/PATCH_PHOTOMETRY_VALIDATION`
 * duck. Each action is a mutation injected into the central `skyportalApi`.
 * The mutations invalidate the `PhotometryValidation` tag.
 */
import type {
  PhotometryValidationOptions,
  PhotometryValidationResponse,
} from "skyportal-js/Photometry";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

interface PhotometryValidationArg {
  id: number | string;
  data?: PhotometryValidationOptions | undefined;
}

export const photometryValidationApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    submitPhotometryValidation: build.mutation<
      PhotometryValidationResponse,
      PhotometryValidationArg
    >({
      queryFn: ({ id, data = {} }, api) =>
        clientQuery(api, (client) =>
          client.postPhotometryValidation(Number(id), data),
        ),
      invalidatesTags: ["PhotometryValidation"],
    }),
    patchPhotometryValidation: build.mutation<
      PhotometryValidationResponse,
      PhotometryValidationArg
    >({
      queryFn: ({ id, data = {} }, api) =>
        clientQuery(api, (client) =>
          client.updatePhotometryValidation(Number(id), data),
        ),
      invalidatesTags: ["PhotometryValidation"],
    }),
    deletePhotometryValidation: build.mutation<
      PhotometryValidationResponse,
      PhotometryValidationArg
    >({
      queryFn: ({ id }, api) =>
        clientQuery(api, (client) =>
          client.deletePhotometryValidation(Number(id)),
        ),
      invalidatesTags: ["PhotometryValidation"],
    }),
  }),
});

export const {
  useSubmitPhotometryValidationMutation,
  usePatchPhotometryValidationMutation,
  useDeletePhotometryValidationMutation,
} = photometryValidationApi;
