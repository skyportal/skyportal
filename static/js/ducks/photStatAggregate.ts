/**
 * Bulk photometry statistics for the Source Statistics page.
 *
 * Wraps `GET /api/phot_stats/aggregate`, which returns compact PhotStat values
 * across many accessible sources (optionally down-selected by classification)
 * for scatter plotting. Call with no axes to fetch the plottable field list.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface PhotStatField {
  value: string;
  label: string;
}

export interface PhotStatPoint {
  id: string;
  ra: number | null;
  dec: number | null;
  classification: string | null;
  x: number | null;
  y: number | null;
  z?: number | null;
}

export interface PhotStatAggregate {
  fields: PhotStatField[];
  points: PhotStatPoint[];
  count: number;
  truncated: boolean;
}

export interface PhotStatAggregateArgs {
  xField?: string;
  yField?: string;
  zField?: string;
  classifications?: string;
  classificationProbThreshold?: number;
  maxMatches?: number;
}

export const photStatAggregateApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getPhotStatAggregate: build.query<PhotStatAggregate, PhotStatAggregateArgs>(
      {
        query: (params) => ({
          url: "api/phot_stats/aggregate",
          params,
        }),
      },
    ),
  }),
});

export const { useGetPhotStatAggregateQuery } = photStatAggregateApi;
