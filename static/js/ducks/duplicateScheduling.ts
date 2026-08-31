/**
 * Objects you have scheduled that another group has scheduled too.
 *
 * The response says only that a clash exists and who to talk to: which object,
 * which group, which instrument. Nothing about either request's payload.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface SchedulingCollision {
  obj_id: string;
  instrument_name: string;
  group_name: string;
  status: string;
}

export const duplicateSchedulingApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDuplicateScheduling: build.query<SchedulingCollision[], void>({
      query: () => "api/duplicate_scheduling",
      providesTags: ["FollowupRequest"],
    }),
  }),
});

export const { useGetDuplicateSchedulingQuery } = duplicateSchedulingApi;
