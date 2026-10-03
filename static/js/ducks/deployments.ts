import { skyportalApi } from "../api/skyportalApi";
import type { components } from "../types/api";

export type Deployments = components["schemas"]["DeploymentsResponse"];
export type Deployment = components["schemas"]["DeploymentResponse"];
export type GitLogEntry = components["schemas"]["GitLogEntryResponse"];
export type InstanceSystem = components["schemas"]["InstanceSystemResponse"];

export const deploymentsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDeployments: build.query<Deployments, void>({
      query: () => "api/deployments",
      providesTags: ["Deployments"],
    }),
  }),
});

export const { useGetDeploymentsQuery } = deploymentsApi;
