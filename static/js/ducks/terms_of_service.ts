import { skyportalApi } from "../api/skyportalApi";

export interface TermsOfService {
  required: boolean;
  version?: string;
  title?: string;
  text?: string;
}

export const termsOfServiceApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTermsOfService: build.query<TermsOfService, void>({
      query: () => "api/terms_of_service",
      providesTags: ["TermsOfService"],
    }),
    acceptTermsOfService: build.mutation<unknown, void>({
      query: () => ({
        url: "api/terms_of_service",
        method: "POST",
      }),
      invalidatesTags: ["TermsOfService"],
    }),
  }),
});

export const { useGetTermsOfServiceQuery, useAcceptTermsOfServiceMutation } =
  termsOfServiceApi;
