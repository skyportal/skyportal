import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import HelpOutlineIcon from "@mui/icons-material/HelpOutlineOutlined";
import Form, { Templates as MuiTemplates } from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { getUiOptions } from "@rjsf/utils";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useGetAllocationsApiClassnameQuery } from "../../ducks/allocations";
import { useSubmitFollowupRequestMutation } from "../../ducks/source";
import GroupShareSelect from "../group/GroupShareSelect";
import Button from "../Button";
import {
  isSomeActiveRangeOrNoRange,
  rangeIsActive,
} from "../allocation/AllocationTable";
import { localeSafeFields } from "./LocaleSafeNumberField";
import { allocationLabel } from "../../utils/format";

const DAY_MS = 24 * 3600 * 1000;

const utcString = (date: string | number) =>
  new Date(date).toISOString().replace("T", " ").slice(0, 19);

const MuiBaseInputTemplate = MuiTemplates.BaseInputTemplate as any;
const FollowupBaseInputTemplate = (props: any) => {
  const { schema, label, hideLabel } = props;
  if (hideLabel || !schema?.description) {
    return <MuiBaseInputTemplate {...props} />;
  }
  return (
    <MuiBaseInputTemplate
      {...props}
      label={
        <Box
          component="span"
          sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}
        >
          {label}
          <Tooltip title={schema.description}>
            <HelpOutlineIcon sx={{ fontSize: "1rem", color: "gray" }} />
          </Tooltip>
        </Box>
      }
    />
  );
};

const MuiFieldTemplate = MuiTemplates.FieldTemplate as any;
const FollowupFieldTemplate = (props: any) => {
  const { schema, uiSchema } = props;
  const widget = getUiOptions(uiSchema).widget;
  // Fields rjsf renders with BaseInputTemplate, whose tooltip already shows the description.
  const usesTooltip =
    !schema?.enum &&
    ["string", "number", "integer"].includes(schema?.type) &&
    widget !== "textarea" &&
    widget !== "checkbox";
  return usesTooltip ? (
    <MuiFieldTemplate
      {...props}
      rawDescription={undefined}
      description={undefined}
    />
  ) : (
    <MuiFieldTemplate {...props} />
  );
};

// Keep stable: an inline object rebuilds rjsf's registry and erases "2.5" mid-typing.
const followupTemplates = {
  BaseInputTemplate: FollowupBaseInputTemplate,
  FieldTemplate: FollowupFieldTemplate,
};

const defaultGroupIds = (allocation: any) =>
  allocation?.default_share_group_ids?.length
    ? allocation.default_share_group_ids
    : [allocation?.group_id];

interface FollowupRequestFormProps {
  obj_id: string;
  instrumentList: any[];
  instrumentFormParams: Record<string, any>;
  requestType?: string;
}

const FollowupRequestForm = ({
  obj_id,
  instrumentList,
  instrumentFormParams,
  requestType = "triggered",
}: FollowupRequestFormProps) => {
  const dispatch = useAppDispatch();
  const [submitFollowupRequestMutation] = useSubmitFollowupRequestMutation();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery();
  const allGroups = useGetGroupsQuery().data?.all;
  const defaultAllocationId = (useGetProfileQuery().data?.preferences as any)
    ?.followupDefault;
  const [selectedAllocationId, setSelectedAllocationId] =
    useState(defaultAllocationId);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[] | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestToConfirm, setRequestToConfirm] = useState<any>(null);

  const isForcedPhotometry = requestType === "forced_photometry";
  const schemaKey = isForcedPhotometry
    ? "formSchemaForcedPhotometry"
    : "formSchema";

  const allocations = useMemo<any[]>(
    () =>
      allocationListApiClassname.filter(
        (allocation: any) =>
          instrumentFormParams[allocation.instrument_id]?.[schemaKey] != null &&
          allocation.types.includes(requestType),
      ),
    [allocationListApiClassname, instrumentFormParams, schemaKey, requestType],
  );
  const allocation =
    allocations.find(({ id }) => id === selectedAllocationId) ?? allocations[0];

  if (!allocation) {
    return (
      <h3>
        {`No allocations with an API class ${
          isForcedPhotometry ? "(for forced photometry) " : ""
        }where found...`}
      </h3>
    );
  }
  if (!allGroups?.length || !telescopeList.length || !instrumentList.length) {
    return <CircularProgress color="secondary" />;
  }

  const groupIds = selectedGroupIds ?? defaultGroupIds(allocation);
  const {
    uiSchema,
    methodsImplemented,
    [schemaKey]: baseSchema,
  } = instrumentFormParams[allocation.instrument_id];

  const submitFollowupRequest = async (formData: any) => {
    setIsSubmitting(true);
    const { data, error }: any = await submitFollowupRequestMutation({
      obj_id,
      allocation_id: allocation.id,
      target_group_ids: groupIds,
      payload: formData,
    });
    if (!error) {
      dispatch(
        data?.request_status?.startsWith("rejected")
          ? showNotification("Request has been rejected.", "warning")
          : showNotification("Request successfully submitted."),
      );
    }
    setIsSubmitting(false);
  };

  const handleSubmit = ({ formData }: { formData?: any }) => {
    if (methodsImplemented.delete) submitFollowupRequest(formData);
    else setRequestToConfirm(formData);
  };

  const validate = (formData: any, errors: any) => {
    const ranges = allocation.validity_ranges;
    if (
      formData?.start_date &&
      formData?.end_date &&
      formData.start_date > formData.end_date
    ) {
      errors.start_date.addError("Start Date must come before End Date");
    }
    const startDate = formData.start_date
      ? new Date(formData.start_date)
      : new Date();
    if (!isSomeActiveRangeOrNoRange(ranges, startDate)) {
      if (formData.start_date) {
        errors.start_date.addError(
          "Start Date must be within an active allocation range",
        );
      } else {
        errors.__errors.push(
          "Current date must be within an active allocation range",
        );
      }
    }
    if (
      formData.end_date &&
      !isSomeActiveRangeOrNoRange(ranges, new Date(formData.end_date))
    ) {
      errors.end_date.addError(
        "End Date must be within an active allocation range",
      );
    }
    return errors;
  };

  let schema = baseSchema;
  const { start_date, end_date } = baseSchema?.properties ?? {};
  if (start_date && end_date) {
    const now = Date.now();
    const [start, end] = isForcedPhotometry
      ? [now - 30 * DAY_MS, now]
      : [
          now,
          now + Date.parse(end_date.default) - Date.parse(start_date.default),
        ];
    const toDefault = (date: number, format?: string) =>
      !isForcedPhotometry && format === "date"
        ? utcString(date).slice(0, 10)
        : utcString(date);
    schema = {
      ...baseSchema,
      properties: {
        ...baseSchema.properties,
        start_date: {
          ...start_date,
          default: toDefault(start, start_date.format),
        },
        end_date: { ...end_date, default: toDefault(end, end_date.format) },
      },
    };
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mb: 2 }}>
      <Box>
        <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="allocationSelectLabel"
          value={allocation.id}
          onChange={(e) => {
            setSelectedAllocationId(e.target.value);
            setSelectedGroupIds(null);
          }}
          name={
            isForcedPhotometry
              ? "forcedPhotometryAllocationSelect"
              : "followupRequestAllocationSelect"
          }
          fullWidth
        >
          {allocations.map((option) => (
            <MenuItem
              value={option.id}
              key={option.id}
              sx={{ whiteSpace: "break-spaces" }}
            >
              {allocationLabel(
                option,
                instrumentList,
                telescopeList,
                allGroups,
              )}
              {!isSomeActiveRangeOrNoRange(option.validity_ranges) && (
                <Tooltip
                  title="This allocation is currently inactive. You can still submit requests for valid future dates."
                  arrow
                >
                  <Typography
                    component="span"
                    sx={{ fontStyle: "italic", color: "grey" }}
                  >
                    {" (inactive)"}
                  </Typography>
                </Tooltip>
              )}
            </MenuItem>
          ))}
        </Select>
      </Box>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <GroupShareSelect
          groupList={allGroups}
          setGroupIDs={setSelectedGroupIds}
          groupIDs={groupIds}
        />
        <Tooltip
          title={
            allocation.validity_ranges?.length
              ? allocation.validity_ranges.map((range: any) => (
                  <Typography
                    key={range.start_date}
                    color={rangeIsActive(range) ? "lightgreen" : "default"}
                  >
                    {`${utcString(range.start_date)} - ${utcString(range.end_date)}`}
                  </Typography>
                ))
              : "No validity ranges defined for this allocation."
          }
          slotProps={{ tooltip: { sx: { maxWidth: 340 } } }}
        >
          <Chip
            label="Validity Ranges"
            size="small"
            icon={<HelpOutlineIcon />}
          />
        </Tooltip>
      </Box>
      <div
        data-testid={
          isForcedPhotometry
            ? "forced-photometry-form"
            : "followup-request-form"
        }
      >
        {/* Remount per allocation so formData doesn't leak across instruments. */}
        <Form
          key={`${allocation.id}-${requestType}`}
          schema={schema}
          validator={validator}
          uiSchema={uiSchema}
          templates={followupTemplates}
          fields={localeSafeFields}
          customValidate={validate}
          onSubmit={handleSubmit}
          disabled={isSubmitting}
        />
      </div>
      {isSubmitting && <CircularProgress />}
      <Dialog
        open={requestToConfirm !== null}
        onClose={() => setRequestToConfirm(null)}
        maxWidth="sm"
      >
        <DialogTitle>Are you sure you want to submit this request?</DialogTitle>
        <DialogContent>
          {`This instrument's API does not implement a delete method, so you
            will not be able to delete this request once it is submitted.`}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              submitFollowupRequest(requestToConfirm);
              setRequestToConfirm(null);
            }}
          >
            Confirm
          </Button>
          <Button onClick={() => setRequestToConfirm(null)}>Cancel</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default FollowupRequestForm;
