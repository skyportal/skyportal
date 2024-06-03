import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import GroupShareSelect from "./group/GroupShareSelect";
import {
  fetchAnalysisServices,
  submitAnalysisService,
} from "../ducks/analysis_services";

dayjs.extend(utc);

const NewAnalysisService = () => {
  const { enum_types } = useSelector((state) => state.enum_types);

  const groups = useSelector((state) => state.groups.userAccessible);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    if (selectedGroupIds.length > 0) {
      formData.group_ids = selectedGroupIds;
    }
    const result = await dispatch(submitAnalysisService(formData));
    if (result.status === "success") {
      dispatch(showNotification("AnalysisService saved"));
      dispatch(fetchAnalysisServices());
    }
  };

  if (enum_types.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const analysisServiceFormSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Analysis Name",
      },
      display_name: {
        type: "string",
        title: "Analysis Display Name",
      },
      description: {
        type: "string",
        title: "Analysis Description",
      },
      version: {
        type: "string",
        title: "Analysis Version",
        default: "1.0",
      },
      contact_name: {
        type: "string",
        title: "Contact Name",
      },
      contact_email: {
        type: "string",
        title: "Contact Email",
      },
      url: {
        type: "string",
        title: "Analysis URL",
      },
      optional_analysis_parameters: {
        type: "string",
        title:
          'Optional analysis parameters (i.e. {"test_parameters": ["test_value_1", "test_value_2"]}',
      },
      input_data_types: {
        type: "array",
        items: {
          type: "string",
          enum: enum_types.ANALYSIS_INPUT_TYPES,
        },
        uniqueItems: true,
        title: "Input data types",
      },
      analysis_type: {
        type: "string",
        oneOf: enum_types.ANALYSIS_TYPES.map((analysis_type) => ({
          enum: [analysis_type],
          title: analysis_type,
        })),
        title: "Analysis Type",
        default: enum_types.ANALYSIS_TYPES[0],
      },
      authentication_type: {
        type: "string",
        oneOf: enum_types.AUTHENTICATION_TYPES.map((authentication_type) => ({
          enum: [authentication_type],
          title: authentication_type,
        })),
        title: "Authentication Type",
        default: enum_types.AUTHENTICATION_TYPES[0],
      },
      timeout: {
        type: "number",
        title: "Analysis Timeout [s]",
        default: 3600,
      },
      _authinfo: {
        type: "string",
        title: "Authentication credentials for the service.",
      },
      is_summary: {
        type: "boolean",
        title: "Establishes the results on the resource as a summary",
        default: false,
      },
      display_on_resource_dropdown: {
        type: "boolean",
        title:
          "Show this analysis service on the analysis dropdown on the resource",
        default: true,
      },
    },
    required: [
      "name",
      "display_name",
      "authentication_type",
      "analysis_type",
      "url",
    ],
  };

  return (
    <div>
      <Form
        schema={analysisServiceFormSchema}
        validator={validator}
        onSubmit={handleSubmit}
        liveValidate
      />
      <GroupShareSelect
        groupList={groups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
    </div>
  );
};

export default NewAnalysisService;
