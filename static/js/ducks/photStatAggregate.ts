/**
 * Bulk photometry statistics for the Source Statistics page.
 *
 * Wraps `GET /api/phot_stats/aggregate`, which returns compact PhotStat values
 * across many accessible sources (optionally down-selected by classification)
 * for scatter plotting. Call with no axes to fetch the plottable field list.
 */
import type {
  PhotStatAggregate,
  PhotStatAggregateField,
  PhotStatAggregatePoint,
} from "skyportal-js/Sources";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

export type {
  PhotStatAggregateField as PhotStatField,
  PhotStatAggregatePoint as PhotStatPoint,
};

export type { PhotStatAggregate };

export interface PhotStatAggregateArgs {
  xField?: string;
  yField?: string;
  zField?: string;
  classifications?: string;
  classificationProbThreshold?: number;
  // Alternatives to classification-based selection.
  group_id?: number;
  obj_ids?: string;
  maxMatches?: number;
}

export const photStatAggregateApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getPhotStatAggregate: build.query<PhotStatAggregate, PhotStatAggregateArgs>(
      {
        queryFn: (params, api) =>
          clientQuery(api, (client) =>
            client.fetchPhotStatsAggregate({
              xField: params.xField,
              yField: params.yField,
              zField: params.zField,
              classifications: params.classifications?.split(","),
              classificationProbThreshold: params.classificationProbThreshold,
              groupId: params.group_id,
              objIds: params.obj_ids?.split(","),
              maxMatches: params.maxMatches,
            }),
          ),
      },
    ),
  }),
});

export const { useGetPhotStatAggregateQuery } = photStatAggregateApi;
