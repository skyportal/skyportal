/**
 * Photometry validation.
 *
 * RTK Query conversion of the old `SUBMIT/DELETE/PATCH_PHOTOMETRY_VALIDATION`
 * duck. Each action is a mutation injected into the central `skyportalApi`.
 * The mutations invalidate the `PhotometryValidation` tag.
 */
import { skyportalApi } from "../api/skyportalApi";

interface PhotometryValidationArg {
  id: number | string;
  data?: Record<string, unknown> | undefined;
}

export const photometryValidationApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    submitPhotometryValidation: build.mutation<
      unknown,
      PhotometryValidationArg
    >({
      query: ({ id, data = {} }) => ({
        url: `api/photometry/${id}/validation`,
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["PhotometryValidation"],
    }),
    patchPhotometryValidation: build.mutation<unknown, PhotometryValidationArg>(
      {
        query: ({ id, data = {} }) => ({
          url: `api/photometry/${id}/validation`,
          method: "PATCH",
          body: data,
        }),
        invalidatesTags: ["PhotometryValidation"],
      },
    ),
    deletePhotometryValidation: build.mutation<
      unknown,
      PhotometryValidationArg
    >({
      query: ({ id }) => ({
        url: `api/photometry/${id}/validation`,
        method: "DELETE",
      }),
      invalidatesTags: ["PhotometryValidation"],
    }),
  }),
});

export const {
  useSubmitPhotometryValidationMutation,
  usePatchPhotometryValidationMutation,
  useDeletePhotometryValidationMutation,
} = photometryValidationApi;
