import { useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Tooltip from "@mui/material/Tooltip";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useAddGCNCrossmatchMutation } from "../../ducks/source";
import Button from "../Button";
import GcnTagsSelect from "../gcn/GcnTagsSelect";
import GcnPropertiesSelect from "../gcn/GcnPropertiesSelect";
import LocalizationTagsSelect from "../localization/LocalizationTagsSelect";
import LocalizationPropertiesSelect from "../localization/LocalizationPropertiesSelect";

dayjs.extend(utc);

const conversions: Record<string, any> = {
  FAR: {
    backendUnit: "Hz",
    frontendUnit: "Per year",
    BackendToFrontend: (val: any) => parseFloat(val) * (365.25 * 24 * 60 * 60),
    FrontendToBackend: (val: any) => parseFloat(val) / (365.25 * 24 * 60 * 60),
  },
};

const comparators: Record<string, string> = {
  lt: "<",
  le: "<=",
  eq: "=",
  ne: "!=",
  ge: ">",
  gt: ">=",
};

const useStyles = makeStyles()(() => ({
  editIcon: {
    cursor: "pointer",
  },
  cuts: {
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    marginTop: "0.5rem",
  },
  tagRow: {
    display: "flex",
    gap: "0.2rem",
  },
}));

interface UpdateSourceGCNCrossmatchProps {
  source: {
    id?: string;
    photstats?: { first_detected_mjd?: number }[];
  };
}

const UpdateSourceGCNCrossmatch = ({
  source,
}: UpdateSourceGCNCrossmatchProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [addGCNCrossmatch] = useAddGCNCrossmatchMutation();

  let firstDet: any = source?.photstats?.[0]?.first_detected_mjd;
  if (firstDet !== undefined && firstDet !== null) {
    firstDet = dayjs.unix((firstDet + 2400000.5 + 0.5 - 2440588) * 86400);
  }

  const [dialogOpen, setDialogOpen] = useState(false);

  // Cuts on which GCN events to crossmatch against.
  const [selectedGcnTags, setSelectedGcnTags] = useState<any[]>([]);
  const [rejectedGcnTags, setRejectedGcnTags] = useState<any[]>([]);
  const [selectedGcnProperties, setSelectedGcnProperties] = useState<any[]>([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState<
    any[]
  >([]);
  const [rejectedLocalizationTags, setRejectedLocalizationTags] = useState<
    any[]
  >([]);
  const [selectedLocalizationProperties, setSelectedLocalizationProperties] =
    useState<any[]>([]);

  const defaultStartDate = firstDet
    ? firstDet.subtract(2, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ")
    : dayjs().subtract(3, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = firstDet
    ? firstDet.add(5, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ")
    : dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");

  // Controlled form data: keep edits in React state so re-renders (e.g. from the
  // tag/property selectors) don't reset the date fields to their defaults.
  const [formData, setFormData] = useState<Record<string, any>>({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
    probability: 0.95,
  });

  const handleSubmit = async () => {
    try {
      await addGCNCrossmatch({
        id: source.id!,
        formData: {
          ...formData,
          gcnTagKeep: selectedGcnTags,
          gcnTagRemove: rejectedGcnTags,
          gcnPropertiesFilter: selectedGcnProperties,
          localizationTagKeep: selectedLocalizationTags,
          localizationTagRemove: rejectedLocalizationTags,
          localizationPropertiesFilter: selectedLocalizationProperties,
        },
      }).unwrap();
      dispatch(
        showNotification(
          "Successfully triggered GCN crossmatch. Please be patient.",
        ),
      );
    } catch {
      dispatch(
        showNotification("Failed to trigger the GCN crossmatch.", "error"),
      );
    }
  };

  const gcnFormSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        format: "date-time",
        title: "Start Date [UTC Time]",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "End Date [UTC Time]",
        default: defaultEndDate,
      },
      probability: {
        type: "number",
        title: "Cumulative Probability",
        default: 0.95,
      },
      beforeFirstDetection: {
        type: "boolean",
        title: "Only GCN events before the source's first detection",
        default: false,
      },
    },
  };

  return (
    <>
      <Tooltip title="Query GCN event crossmatch">
        <EditIcon
          data-testid="updateMPCIconButton"
          fontSize="small"
          className={classes.editIcon}
          onClick={() => {
            setDialogOpen(true);
          }}
        />
      </Tooltip>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Query GCN Event Crossmatch</DialogTitle>
        <DialogContent>
          <Form
            schema={gcnFormSchema as any}
            formData={formData}
            onChange={((e: any) => setFormData(e.formData)) as any}
            validator={validator}
            onSubmit={handleSubmit as any}
          >
            <div className={classes.cuts}>
              <Divider>Filter which GCN events to crossmatch</Divider>
              <Box className={classes.tagRow}>
                <GcnTagsSelect
                  title="GCN Tags to Keep"
                  selectedGcnTags={selectedGcnTags}
                  setSelectedGcnTags={setSelectedGcnTags}
                />
                <GcnTagsSelect
                  title="GCN Tags to Reject"
                  selectedGcnTags={rejectedGcnTags}
                  setSelectedGcnTags={setRejectedGcnTags}
                />
              </Box>
              <GcnPropertiesSelect
                selectedGcnProperties={selectedGcnProperties}
                setSelectedGcnProperties={setSelectedGcnProperties}
                conversions={conversions}
                comparators={comparators}
              />
              <Box className={classes.tagRow}>
                <LocalizationTagsSelect
                  title="Localization Tags to Keep"
                  selectedLocalizationTags={selectedLocalizationTags}
                  setSelectedLocalizationTags={setSelectedLocalizationTags}
                />
                <LocalizationTagsSelect
                  title="Localization Tags to Reject"
                  selectedLocalizationTags={rejectedLocalizationTags}
                  setSelectedLocalizationTags={setRejectedLocalizationTags}
                />
              </Box>
              <LocalizationPropertiesSelect
                selectedLocalizationProperties={selectedLocalizationProperties}
                setSelectedLocalizationProperties={
                  setSelectedLocalizationProperties
                }
                comparators={comparators}
              />
              <Button primary type="submit" style={{ marginTop: "0.5rem" }}>
                Query Crossmatch
              </Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UpdateSourceGCNCrossmatch;
