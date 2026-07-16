/**
 * NASA ACROSS joint visibility.
 *
 * RTK Query endpoints (injected into `skyportalApi`). `getAcrossInstruments`
 * lists the SkyPortal instruments backed by an ACROSS instrument (populated by
 * tools/load_across_instruments.py); `getAcrossJointVisibility` returns
 * per-instrument visibility windows for a source plus their local intersection
 * (joint windows). See https://across.sciencecloud.nasa.gov
 */
import { skyportalApi } from "../api/skyportalApi";

export interface AcrossInstrument {
  id: number;
  name: string;
  telescope_id: number;
  telescope_name: string | null;
}

export interface AcrossVisibilityWindow {
  begin: string;
  end: string;
  duration_hr: number;
  start_reason: string | null;
  end_reason: string | null;
}

export interface AcrossSingleVisibility {
  id: number;
  name: string;
  kind: "ground" | "space";
  windows: AcrossVisibilityWindow[];
  error: string | null;
}

export interface AcrossJointVisibility {
  begin: string;
  end: string;
  single: AcrossSingleVisibility[];
  joint: AcrossVisibilityWindow[];
  ground_max_airmass: number;
}

interface AcrossQueryArgs {
  objId: string;
  telescopeIds: number[];
  begin?: string;
  end?: string;
}

export const acrossApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getAcrossInstruments: build.query<AcrossInstrument[], void>({
      query: () => ({ url: "api/internal/across/instruments" }),
    }),
    getAcrossJointVisibility: build.query<
      AcrossJointVisibility,
      AcrossQueryArgs
    >({
      query: ({ objId, telescopeIds, begin, end }) => ({
        url: `api/internal/across/joint_visibility/${objId}`,
        params: {
          telescopeIds,
          ...(begin ? { begin } : {}),
          ...(end ? { end } : {}),
        },
      }),
    }),
  }),
});

export const {
  useGetAcrossInstrumentsQuery,
  useGetAcrossJointVisibilityQuery,
} = acrossApi;
