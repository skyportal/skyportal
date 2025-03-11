import * as API from "../API";

const POST_MOVING_OBJECT_OBSPLAN = "skyportal/POST_MOVING_OBJECT_OBSPLAN";

export const postMovingObjectObsPlan = (name, data) =>
  API.POST(
    `/api/moving_object/${name}/followup`,
    POST_MOVING_OBJECT_OBSPLAN,
    data,
  );

// For now we do not need a message handler or a reducer for this action
