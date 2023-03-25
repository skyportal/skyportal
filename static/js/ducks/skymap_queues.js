import * as API from "../API";

const REQUEST_API_SKYMAP_QUEUES = "skyportal/REQUEST_API_SKYMAP_QUEUES";

const PUT_API_SKYMAP_QUEUE = "skyportal/PUT_API_SKYMAP_QUEUE";

const DELETE_API_SKYMAP_QUEUE = "skyportal/DELETE_API_SKYMAP_QUEUE";

export function requestAPISkymapQueues(id, data = { queuesOnly: true }) {
  return API.GET(`/api/skymap_queue/${id}`, REQUEST_API_SKYMAP_QUEUES, data);
}

export function postAPISkymapQueue(data) {
  return API.POST("/api/skymap_queue", PUT_API_SKYMAP_QUEUE, data);
}

export function deleteAPISkymapQueue(id, data = {}) {
  return API.DELETE(`/api/skymap_queue/${id}`, DELETE_API_SKYMAP_QUEUE, data);
}
