import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SmartToyTwoToneIcon from "@mui/icons-material/SmartToyTwoTone";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import Tooltip from "@mui/material/Tooltip";

import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as analysisServicesActions from "../ducks/analysis_services";
import * as sourceActions from "../ducks/source";
import GroupShareSelect from "./group/GroupShareSelect";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "1rem",
    cursor: "pointer",
  },
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

const StartBotSummary = ({ obj_id }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { analysisServiceList } = useSelector(
    (state) => state.analysis_services,
  );

  const uniqueNames = [
    ...new Set(analysisServiceList.map((item) => item.name)),
  ];
  const uniqueAnalysisServiceList = uniqueNames.map((name) =>
    analysisServiceList.find((item) => item.name === name),
  );
  const allGroups = useSelector((state) => state.groups.all);
  const prefs = useSelector((state) => state.profile.preferences);
  const config = useSelector((state) => state.config);

  const [selectedAnalysisServiceId, setSelectedAnalysisServiceId] =
    useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      let data = [];
      if (!analysisServiceList || analysisServiceList.length === 0) {
        const result = await dispatch(
          analysisServicesActions.fetchAnalysisServices(),
        );
        data = result?.data || [];
      } else {
        data = analysisServiceList;
      }
      setSelectedAnalysisServiceId(data[0]?.id);
    };
    getAnalysisServices();
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

    const params = {
      show_parameters: true,
      show_plots: false,
      show_corner: false,
      analysis_parameters,
    };

    if (selectedGroupIds.length >= 0) {
      params.group_ids = selectedGroupIds;
    }
    await dispatch(
      sourceActions.startAnalysis(obj_id, selectedAnalysisServiceId, params),
    );
    setIsSubmitting(false);
    setDialogOpen(false);
  };

  const handleSelectedAnalysisServiceChange = (e) => {
    setSelectedAnalysisServiceId(e.target.value);
  };

  const OptionalParameters = {};

  const AnalysisSelectionFormSchema = {
    type: "object",
    properties: {
      ...OptionalParameters,
    },
  };

  const showBotIcon = () => {
    if (
      analysisServiceList?.filter((service) => service.is_summary).length > 0 &&
      (prefs?.summary?.OpenAI?.active === true ||
        config?.openai_summary_apikey_set === true)
    ) {
      return true;
    }
    return false;
  };

  return (
    <>
      {showBotIcon() ? (
        <Tooltip title="Start AI Summary">
          <span>
            <SmartToyTwoToneIcon
              data-testid="runSummaryIconButton"
              fontSize="small"
              className={classes.editIcon}
              onClick={() => {
                setDialogOpen(true);
              }}
            />
          </span>
        </Tooltip>
      ) : null}
      <Dialog
        open={dialogOpen}
        maxWidth="sm"
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Run AI Summary</DialogTitle>
        <DialogContent>
          <div>
            <InputLabel id="analysisServiceSelectLabel">
              Select AI Summary Service
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
                  analysisService.is_summary && (
                    <MenuItem
                      value={analysisService.id}
                      key={analysisService.id}
                      className={classes.SelectItem}
                    >
                      {analysisService.name}
                    </MenuItem>
                  ),
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
        </DialogContent>
      </Dialog>
    </>
  );
};

StartBotSummary.propTypes = {
  obj_id: PropTypes.string.isRequired,
};

export default StartBotSummary;
