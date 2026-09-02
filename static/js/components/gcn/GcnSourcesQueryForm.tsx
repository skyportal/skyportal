import { useState } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import Button from "../Button";
import {
  CROSSMATCH_ORIGIN,
  buildAnnotationFilters,
} from "./gcnSourcesAnnotationFilters";

/** The source query's own parameters.
 *
 * Only what the sources endpoint reads for a localization search. The galaxy
 * catalog and maximum distance live on the Galaxies tab, since the sources
 * query does not accept them.
 *
 * "Require detections" here means detected *during* the time range, not that
 * the whole detection history falls inside it, which would drop any transient
 * still being detected. The range is sent as a detection window for that
 * reason (see fetchGcnEventSources).
 *
 * The star, detection history and galactic latitude cuts are on by default, as
 * the scanning guidelines call for. The latitude and history cuts apply only
 * beyond promptDeltaT days of the event, so a counterpart seen promptly is
 * shown wherever it sits; every cut can be cleared for a search that wants the
 * unfiltered list.
 */
const sourcesFormSchema = (
  defaultStartDate: string,
  defaultEndDate: string,
  groups: any[],
) => ({
  type: "object",
  properties: {
    startDate: {
      type: "string",
      format: "date-time",
      title: "Detected after",
      default: defaultStartDate,
    },
    endDate: {
      type: "string",
      format: "date-time",
      title: "Detected before",
      default: defaultEndDate,
    },
    localizationCumprob: {
      type: "number",
      title: "Cumulative Probability",
      default: 0.95,
      minimum: 0,
      maximum: 1,
    },
    numberDetections: {
      type: "number",
      title: "Min Number of Detections",
      default: 2,
      minimum: 1,
    },
    requireDetections: {
      type: "boolean",
      title: "Require detections",
      default: true,
    },
    excludeForcedPhotometry: {
      type: "boolean",
      title: "Exclude forced photometry",
      default: false,
    },
    localizationRejectSources: {
      type: "boolean",
      title: "Do not display rejected sources",
      default: true,
    },
    group_ids: {
      type: "array",
      items: { type: "number", anyOf: groups.map((g) => ({ const: g.id })) },
      uniqueItems: true,
      default: [] as number[],
      title: "Groups",
    },
    maxSgscore: {
      type: "number",
      title: "Max star score (sgscore)",
      default: 0.7,
      minimum: 0,
      maximum: 1,
    },
    maxAge: {
      type: "number",
      title: "Max age at detection [days]",
      minimum: 0,
    },
    minNdethist: {
      type: "number",
      title: "Min detections in history",
      default: 2,
      minimum: 1,
    },
    minDeltaT: {
      type: "number",
      title: "Earliest detection relative to event [days]",
    },
    minAbsGalacticLatitude: {
      type: "number",
      title: "Min |galactic latitude| [deg]",
      default: 10,
      minimum: 0,
      maximum: 90,
    },
    promptDeltaT: {
      type: "number",
      title: "Always show within [days] of event",
      default: 2,
      minimum: 0,
    },
  },
  required: [
    "startDate",
    "endDate",
    "localizationCumprob",
    "requireDetections",
  ],
});

const uiSchema = (groups: any[]) => ({
  group_ids: { "ui:enumNames": groups.map((group) => group.name) },
  "ui:grid": [
    { startDate: 6, endDate: 6 },
    { localizationCumprob: 4, numberDetections: 4, group_ids: 4 },
    {
      requireDetections: 4,
      excludeForcedPhotometry: 4,
      localizationRejectSources: 4,
    },
    { maxSgscore: 3, maxAge: 3, minNdethist: 3, minDeltaT: 3 },
    { minAbsGalacticLatitude: 3, promptDeltaT: 3 },
  ],
});

/** Inline validation, so a bad range is caught before the query runs. */
const validate = (formData: any, errors: any) => {
  if (
    formData.startDate &&
    formData.endDate &&
    formData.startDate > formData.endDate
  ) {
    errors.startDate.addError("Start Date must come before End Date");
  }
  if (formData.localizationCumprob < 0 || formData.localizationCumprob > 1.01) {
    errors.localizationCumprob.addError(
      "Cumulative probability should be between 0 and 1",
    );
  }
  // Querying sources requires a group; surface it inline rather than as a
  // notification once the query has already been sent.
  if (!formData.group_ids?.length) {
    errors.group_ids.addError("Select at least one group.");
  }
  return errors;
};

interface GcnSourcesQueryFormProps {
  defaultStartDate: string;
  defaultEndDate: string;
  groups: any[];
  isSubmitting?: boolean;
  onSearch: (formData: Record<string, any>) => void;
}

const GcnSourcesQueryForm = ({
  defaultStartDate,
  defaultEndDate,
  groups,
  isSubmitting,
  onSearch,
}: GcnSourcesQueryFormProps) => {
  const [formData, setFormData] = useState<Record<string, any>>({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
    localizationCumprob: 0.95,
    numberDetections: 2,
    requireDetections: true,
    excludeForcedPhotometry: false,
    localizationRejectSources: true,
    maxSgscore: 0.7,
    minNdethist: 2,
    minAbsGalacticLatitude: 10,
    promptDeltaT: 2,
  });

  return (
    <div data-testid="gcn-sources-form" style={{ marginBottom: "1rem" }}>
      <Form
        schema={
          sourcesFormSchema(defaultStartDate, defaultEndDate, groups) as any
        }
        formData={formData}
        onChange={((e: any) => setFormData(e.formData)) as any}
        uiSchema={uiSchema(groups) as any}
        validator={validator}
        customValidate={validate as any}
        onSubmit={
          (({ formData: submitted }: any) => {
            const { maxSgscore, maxAge, minNdethist, minDeltaT, ...rest } =
              submitted;
            const annotationsFilter = buildAnnotationFilters(submitted);
            onSearch(
              annotationsFilter.length
                ? {
                    ...rest,
                    annotationsFilter: annotationsFilter.join(","),
                    annotationsFilterOrigin: CROSSMATCH_ORIGIN,
                  }
                : rest,
            );
          }) as any
        }
        disabled={!!isSubmitting}
      >
        <Button primary type="submit" async loading={!!isSubmitting}>
          Find sources
        </Button>
      </Form>
    </div>
  );
};

export default GcnSourcesQueryForm;
