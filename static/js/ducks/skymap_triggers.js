import * as API from "../API";

const REQUEST_API_SKYMAP_TRIGGERS = "skyportal/REQUEST_API_SKYMAP_TRIGGERS";

const PUT_API_SKYMAP_TRIGGER = "skyportal/PUT_API_SKYMAP_TRIGGER";

const DELETE_API_SKYMAP_TRIGGER = "skyportal/DELETE_API_SKYMAP_TRIGGER";

export function requestAPISkymapTriggers(id, data = { triggersOnly: true }) {
  return API.GET(
    `/api/skymap_trigger/${id}`,
    REQUEST_API_SKYMAP_TRIGGERS,
    data,
  );
}

export function postAPISkymapTrigger(data) {
  return API.POST("/api/skymap_trigger", PUT_API_SKYMAP_TRIGGER, data);
}

export function deleteAPISkymapTrigger(id, data = {}) {
  return API.DELETE(
    `/api/skymap_trigger/${id}`,
    DELETE_API_SKYMAP_TRIGGER,
    data,
  );
}
