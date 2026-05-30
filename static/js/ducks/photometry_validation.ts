import * as API from "../API";

const SUBMIT_PHOTOMETRY_VALIDATION = "skyportal/SUBMIT_PHOTOMETRY_VALIDATION";

const DELETE_PHOTOMETRY_VALIDATION = "skyportal/DELETE_PHOTOMETRY_VALIDATION";

const PATCH_PHOTOMETRY_VALIDATION = "skyportal/PATCH_PHOTOMETRY_VALIDATION";

export const submitValidation = (
  id: number | string,
  data: Record<string, any> = {},
) =>
  API.POST(
    `/api/photometry/${id}/validation`,
    SUBMIT_PHOTOMETRY_VALIDATION,
    data,
  );

export const deleteValidation = (id: number | string) =>
  API.DELETE(`/api/photometry/${id}/validation`, DELETE_PHOTOMETRY_VALIDATION);

export const patchValidation = (
  id: number | string,
  data: Record<string, any> = {},
) =>
  API.PATCH(
    `/api/photometry/${id}/validation`,
    PATCH_PHOTOMETRY_VALIDATION,
    data,
  );
