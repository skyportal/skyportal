import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as analysisServicesActions from "../ducks/analysis_services";
import * as sourceActions from "../ducks/source";
import GroupShareSelect from "./GroupShareSelect";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  marginTop: {
    marginTop: "1rem",
  },
  Select: {
    width: "100%",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
    "& > *": {
      marginTop: "1rem",
      marginBottom: "1rem",
    },
  },
}));

const AnalysisForm = ({ obj_id }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { analysisServiceList } = useSelector(
    (state) => state.analysis_services
  );
  const uniqueNames = [
    ...new Set(analysisServiceList.map((item) => item.name)),
  ];
  const uniqueAnalysisServiceList = uniqueNames.map((name) =>
    analysisServiceList.find((item) => item.name === name)
  );
  const allGroups = useSelector((state) => state.groups.all);
  const [selectedAnalysisServiceId, setSelectedAnalysisServiceId] =
    useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFetching, setIsFetching] = useState(false);

  const groupLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allGroups?.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const analysisServiceLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  analysisServiceList?.forEach((analysisService) => {
    analysisServiceLookUp[analysisService.id] = analysisService;
  });

  useEffect(() => {
    const getAnalysisServices = async () => {
      setIsFetching(true);
      const result = await dispatch(
        analysisServicesActions.fetchAnalysisServices()
      );
      setIsFetching(false);
      const { data } = result;
      setSelectedAnalysisServiceId(data[0]?.id);
    };
    if (
      (!analysisServiceList || analysisServiceList.length === 0) &&
      !isFetching
    ) {
      getAnalysisServices();
    } else if (
      analysisServiceList &&
      analysisServiceList.length > 0 &&
      !selectedAnalysisServiceId
    ) {
      setSelectedAnalysisServiceId(analysisServiceList[0].id);
    }
  }, [dispatch, setSelectedAnalysisServiceId]);

  if (
    !allGroups ||
    allGroups.length === 0 ||
    !analysisServiceList ||
    analysisServiceList.length === 0 ||
    !selectedAnalysisServiceId
  ) {
    return null;
  }

  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    const analysis_parameters = {
      ...formData,
    };

    delete analysis_parameters.show_parameters;
    delete analysis_parameters.show_plots;
    delete analysis_parameters.show_corner;

    const params = {
      show_parameters: formData.show_parameters,
      show_plots: formData.show_plots,
      show_corner: formData.show_corner,
      analysis_parameters,
    };

    if (selectedGroupIds.length >= 0) {
      params.group_ids = selectedGroupIds;
    }
    await dispatch(
      sourceActions.startAnalysis(obj_id, selectedAnalysisServiceId, params)
    );
    setIsSubmitting(false);
  };

  const handleSelectedAnalysisServiceChange = (e) => {
    setSelectedAnalysisServiceId(e.target.value);
  };

  const OptionalParameters = {};
  const RequiredParameters = [];
  if (
    analysisServiceLookUp[selectedAnalysisServiceId]
      ?.optional_analysis_parameters
  ) {
    const keys = Object.keys(
      analysisServiceLookUp[selectedAnalysisServiceId]
        .optional_analysis_parameters
    );
    keys.forEach((key) => {
      const params =
        analysisServiceLookUp[selectedAnalysisServiceId]
          ?.optional_analysis_parameters[key];

      if (Array.isArray(params)) {
        if (["True", "False"].every((val) => params.includes(val))) {
          OptionalParameters[key] = { type: "boolean" };
        } else {
          OptionalParameters[key] = { type: "string", enum: params };
          RequiredParameters.push(key);
        }
      } else if (typeof params === "object") {
        if (params?.type === "number") {
          OptionalParameters[key] = {
            type: "number",
            title: key,
          };
        } else if (params?.type === "file") {
          OptionalParameters[key] = {
            type: "string",
            format: "data-url",
            title: key,
            description: key, // we set a description by default for file as the title doesn't show up in the rjsf form
          };
        } else if (params?.type === "string") {
          OptionalParameters[key] = {
            type: "string",
            title: key,
          };
        }

        if (params?.default) {
          OptionalParameters[key].default = params.default;
        }

        if (params?.description) {
          OptionalParameters[key].description = params.description;
        }

        if (params?.title) {
          OptionalParameters[key].title = params.title;
        }

        if (params?.required) {
          if (["True", "true", "t"].includes(params.required)) {
            RequiredParameters.push(key);
          }
        }
      } else {
        OptionalParameters[key] = { type: "string", enum: params };
        RequiredParameters.push(key);
      }
    });
  }

  const AnalysisSelectionFormSchema = {
    type: "object",
    properties: {
      ...OptionalParameters,
      show_parameters: {
        type: "boolean",
        title: "Show Parameters",
        description: "Whether to render the parameters of this analysis",
        default: true,
      },
      show_plots: {
        type: "boolean",
        title: "Show Plots",
        description: "Whether to render the plots of this analysis",
        default: true,
      },
      show_corner: {
        type: "boolean",
        title: "Show Corner",
        description: "Whether to render the corner of this analysis",
        default: true,
      },
    },
    required: ["show_parameters", "show_plots", "show_corner"].concat(
      RequiredParameters
    ),
  };

  return (
    <div className={classes.container}>
      <div>
        <InputLabel id="analysisServiceSelectLabel">
          Start New Analysis
        </InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="analysisServiceSelectLabel"
          value={selectedAnalysisServiceId || ""}
          onChange={handleSelectedAnalysisServiceChange}
          name="analysisServiceSelect"
          data-testid="analysisServiceSelect"
          className={classes.Select}
        >
          {uniqueAnalysisServiceList?.map(
            (analysisService) =>
              analysisService.display_on_resource_dropdown !== false && (
                <MenuItem
                  value={analysisService.id}
                  key={analysisService.id}
                  className={classes.SelectItem}
                >
                  {analysisService.name}
                </MenuItem>
              )
          )}
        </Select>
      </div>
      <GroupShareSelect
        groupList={allGroups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
      <div data-testid="analysis-service-request-form">
        <div>
          <Form
            schema={AnalysisSelectionFormSchema}
            validator={validator}
            onSubmit={handleSubmit}
            // eslint-disable-next-line react/jsx-no-bind
            disabled={isSubmitting}
            liveValidate
          />
        </div>
        {isSubmitting && (
          <div className={classes.marginTop}>
            <CircularProgress />
          </div>
        )}
      </div>
    </div>
  );
};

AnalysisForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
};

export default AnalysisForm;
