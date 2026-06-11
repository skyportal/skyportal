import { useGetProfileQuery } from "../ducks/profile";
import { useGetGroupsQuery } from "../ducks/groups";
import { useEffect, useMemo, useState } from "react";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import SmartToyTwoToneIcon from "@mui/icons-material/SmartToyTwoTone";
import IconButton from "@mui/material/IconButton";
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
import { useGetConfigQuery } from "../ducks/config";

dayjs.extend(relativeTime);
dayjs.extend(utc);

interface StartBotSummaryProps {
  obj_id: string;
}

const StartBotSummary = ({ obj_id }: StartBotSummaryProps) => {
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
  const { data: config } = useGetConfigQuery() as { data: any };

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
    !allGroups?.length ||
    !analysisServiceList?.length ||
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

  if (
    !analysisServiceList?.some((service: any) => service.is_summary) ||
    (!prefs?.summary?.OpenAI?.active && !config?.openai_summary_apikey_set)
  ) {
    return null;
  }

  return (
    <>
      <Tooltip title="Start AI Summary">
        <IconButton size="small" onClick={() => setDialogOpen(true)}>
          <SmartToyTwoToneIcon fontSize="small" />
        </IconButton>
      </Tooltip>
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
              labelId="analysisServiceSelectLabel"
              value={selectedAnalysisServiceId || ""}
              onChange={handleSelectedAnalysisServiceChange}
              name="analysisServiceSelect"
              fullWidth
            >
              {uniqueAnalysisServiceList?.map(
                (analysisService: any) =>
                  analysisService.is_summary && (
                    <MenuItem
                      value={analysisService.id}
                      key={analysisService.id}
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
          <Form
            schema={AnalysisSelectionFormSchema as any}
            validator={validator}
            onSubmit={handleSubmit as any}
            disabled={isSubmitting}
            liveValidate
          />
          {isSubmitting && <CircularProgress />}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default StartBotSummary;
