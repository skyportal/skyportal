import * as API from "../API";
import store from "../store";
import { brokerFilterBase } from "./brokerFilterTarget";

import {
  ztf_crossmatch_fields,
  lsst_crossmatch_fields,
} from "../constants/crossmatch";

export const FETCH_ALL_ELEMENTS = "skyportal/FETCH_ALL_ELEMENTS";
export const FETCH_ALL_ELEMENTS_OK = "skyportal/FETCH_ALL_ELEMENTS_OK";
export const FETCH_ALL_ELEMENTS_ERROR = "skyportal/FETCH_ALL_ELEMENTS_ERROR";
export const FETCH_ALL_ELEMENTS_FAIL = "skyportal/FETCH_ALL_ELEMENTS_FAIL";

export const FETCH_ELEMENT = "skyportal/FETCH_ELEMENT";
export const FETCH_ELEMENT_OK = "skyportal/FETCH_ELEMENT_OK";

export const FETCH_SCHEMA = "skyportal/FETCH_SCHEMA";
export const FETCH_SCHEMA_OK = "skyportal/FETCH_SCHEMA_OK";

export const POST_ELEMENT = "skyportal/POST_ELEMENT";
export const POST_ELEMENT_OK = "skyportal/POST_ELEMENT_OK";

export const PUT_ELEMENT = "skyportal/PUT_ELEMENT";
export const PUT_ELEMENT_OK = "skyportal/PUT_ELEMENT_OK";

export function fetchAllElements({ elements }) {
  return API.GET(`${brokerFilterBase()}/filter_modules`, FETCH_ALL_ELEMENTS, {
    elements,
  });
}

export function fetchElement({ survey, elements }) {
  return API.GET(`${brokerFilterBase()}/filter_modules`, FETCH_ELEMENT, {
    elements,
    survey,
  });
}

export function fetchSchema(survey) {
  return API.GET(`${brokerFilterBase()}/filter_modules`, FETCH_SCHEMA, {
    survey,
    elements: "schema",
  });
}

export function postElement({ name, data, elements }) {
  return API.POST(
    `${brokerFilterBase()}/filter_modules/${name}`,
    POST_ELEMENT,
    {
      data,
      elements,
    },
  );
}

export function putElement({ name, data, elements }) {
  return API.PUT(`${brokerFilterBase()}/filter_modules/${name}`, PUT_ELEMENT, {
    data,
    elements,
  });
}

const patchSchema = (schema) => {
  if (!schema) return schema;

  const patchedSchema = JSON.parse(JSON.stringify(schema));

  if (patchedSchema.fields) {
    if (patchedSchema.name.includes("Ztf")) {
      patchedSchema.fields.push(ztf_crossmatch_fields);
    }
    if (patchedSchema.name.includes("Lsst")) {
      patchedSchema.fields.push(lsst_crossmatch_fields);
    }
  }

  return patchedSchema;
};

const reducer = (state = {}, action) => {
  switch (action.type) {
    case FETCH_SCHEMA_OK: {
      try {
        const schema_from_db = action.data.schema;
        const patchedSchema = patchSchema(schema_from_db);
        const res = { schema: patchedSchema };
        return res;
      } catch (error) {
        console.error("Error parsing schema JSON:", error);
        return { schema: null };
      }
    }
    case FETCH_ELEMENT_OK:
    case FETCH_ALL_ELEMENTS_OK: {
      return action.data;
    }
    case FETCH_ALL_ELEMENTS_FAIL:
    case FETCH_ALL_ELEMENTS_ERROR: {
      return {};
    }
    default:
      return state;
  }
};

store.injectReducer("filter_modules", reducer);
