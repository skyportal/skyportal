export const surveyOf = (candidate: any): string | undefined =>
  candidate.thumbnails?.find((t: any) => t.obj_id === candidate.id && t.survey)
    ?.survey ??
  candidate.photstats?.[0]?.last_detected_filter
    ?.match(/^(ztf|lsst|decam)/i)?.[1]
    .toUpperCase();
