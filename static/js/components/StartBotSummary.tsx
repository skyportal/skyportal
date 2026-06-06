import { useGetProfileQuery } from "../ducks/profile";
import { useGetGroupsQuery } from "../ducks/groups";
import { useEffect, useMemo, useState } from "react";
import { useAppSelector } from "../types/hooks";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import SmartToyTwoToneIcon from "@mui/icons-material/SmartToyTwoTone";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import Tooltip from "@mui/material/Tooltip";

import MenuItem from "@mui/material/MenuItem";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { useGetAnalysisServicesQuery } from "../ducks/analysis_services";
import { useStartAnalysisMutation } from "../ducks/source";
import GroupShareSelect from "./group/GroupShareSelect";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
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

interface StartBotSummaryProps {
  obj_id: string;
}

const StartBotSummary = ({ obj_id }: StartBotSummaryProps) => {
  const { classes } = useStyles();
  const [startAnalysis] = useStartAnalysisMutation();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: analysisServiceListData } = useGetAnalysisServicesQuery();
  const analysisServiceList = useMemo(
    () => analysisServiceListData ?? [],
    [analysisServiceListData],
  );

  const uniqueNames = [
    ...new Set(analysisServiceList.map((item: any) => item.name)),
  ];
  const uniqueAnalysisServiceList = uniqueNames.map((name) =>
    analysisServiceList.find((item: any) => item.name === name),
  );
  const allGroups = useGetGroupsQuery().data?.all ?? null;
  const prefs: any = useGetProfileQuery().data?.preferences;
  const config = useAppSelector((state) => state["config"]);

  const [selectedAnalysisServiceId, setSelectedAnalysisServiceId] =
    useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const groupLookUp: Record<string, any> = {};

  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const analysisServiceLookUp: Record<string, any> = {};

  analysisServiceList?.forEach((analysisService: any) => {
    analysisServiceLookUp[analysisService.id] = analysisService;
  });

  useEffect(() => {
    if (selectedAnalysisServiceId == null && analysisServiceList.length > 0) {
      setSelectedAnalysisServiceId(analysisServiceList[0]?.id);
    }
  }, [analysisServiceList, selectedAnalysisServiceId]);

  if (
    !allGroups ||
    allGroups.length === 0 ||
    !analysisServiceList ||
    analysisServiceList.length === 0 ||
    !selectedAnalysisServiceId
  ) {
    return null;
  }

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setIsSubmitting(true);
    const analysis_parameters = {
      ...formData,
    };

    const params: any = {
      show_parameters: true,
      show_plots: false,
      show_corner: false,
      analysis_parameters,
    };

    if (selectedGroupIds.length >= 0) {
      params.group_ids = selectedGroupIds;
    }
    await startAnalysis({
      id: obj_id,
      analysis_service_id: selectedAnalysisServiceId,
      formData: params,
    });
    setIsSubmitting(false);
    setDialogOpen(false);
  };

  const handleSelectedAnalysisServiceChange = (e: any) => {
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
      analysisServiceList?.filter((service: any) => service.is_summary).length >
        0 &&
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
        onClose={() => setDialogOpen(false)}
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
                (analysisService: any) =>
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
                schema={AnalysisSelectionFormSchema as any}
                validator={validator}
                onSubmit={handleSubmit as any}
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

export default StartBotSummary;
