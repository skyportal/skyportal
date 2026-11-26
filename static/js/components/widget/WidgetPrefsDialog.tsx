import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";

import { useGetGroupsQuery } from "../../ducks/groups";
import SearchableSelect from "../SearchableSelect";
import Button from "../Button";

const LABELS: Record<string, string> = {
  numItems: "Number of items",
  maxNumSources: "Number of sources",
  maxNumSavers: "Number of users",
  maxNumEvents: "Number of events",
  sinceDaysAgo: "Number of days",
  includeSitewideSources: "Include sitewide sources",
  displayTNS: "Show TNS names",
  candidatesOnly: "Only if source has candidate(s)",
  categories: "Show",
  includeCommentsFromBots: "Comments from bots",
};

const labelFor = (key: string) =>
  LABELS[key] ?? key.charAt(0).toUpperCase() + key.slice(1);

const isPlainObject = (value: any) =>
  typeof value === "object" && value !== null && value.constructor === Object;

interface WidgetPrefsDialogProps {
  title: string;
  initialValues: Record<string, any>;
  onSubmit: (...args: any[]) => any;
  stateBranchName: string;
}

const WidgetPrefsDialog = ({
  title,
  initialValues,
  onSubmit,
  stateBranchName,
}: WidgetPrefsDialogProps) => {
  const [open, setOpen] = useState(false);
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];

  const {
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm({ defaultValues: initialValues });

  const handleOpen = () => {
    reset(initialValues);
    setOpen(true);
  };

  const formSubmit = (formData: any) => {
    onSubmit({ [stateBranchName]: formData });
    setOpen(false);
  };

  const renderField = (key: string) => {
    const initial = initialValues[key];
    if (isPlainObject(initial)) {
      return (
        <Box key={key}>
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
            {labelFor(key)}
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
            {Object.keys(initial).map((subKey) => {
              const checkbox = (
                <FormControlLabel
                  key={subKey}
                  control={
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <Checkbox
                          size="small"
                          onChange={(event) => onChange(event.target.checked)}
                          checked={value}
                          data-testid={`${key}.${subKey}`}
                        />
                      )}
                      name={`${key}.${subKey}`}
                      control={control}
                      defaultValue={false}
                    />
                  }
                  label={labelFor(subKey)}
                />
              );
              return subKey === "includeCommentsFromBots" ? (
                <Tooltip
                  key={subKey}
                  placement="right"
                  title="Bot comments are those posted programmatically using API tokens"
                >
                  {checkbox}
                </Tooltip>
              ) : (
                checkbox
              );
            })}
          </Box>
        </Box>
      );
    }
    if (typeof initial === "string") {
      return (
        <Controller
          key={key}
          render={({ field: { onChange, value } }) => (
            <TextField
              data-testid={key}
              size="small"
              label={labelFor(key)}
              name={key}
              error={!!errors[key]}
              helperText={errors[key] ? "Required" : ""}
              onChange={onChange}
              value={value}
              fullWidth
              slotProps={{ htmlInput: { inputMode: "numeric" } }}
            />
          )}
          name={key}
          control={control}
          rules={{ required: true }}
          defaultValue={initial}
        />
      );
    }
    if (typeof initial === "boolean") {
      return (
        <Controller
          key={key}
          render={({ field: { onChange, value } }) => (
            <FormControlLabel
              sx={{ mt: -1 }}
              control={
                <Checkbox
                  size="small"
                  onChange={(event) => onChange(event.target.checked)}
                  checked={value}
                  data-testid={key}
                />
              }
              label={labelFor(key)}
            />
          )}
          name={key}
          control={control}
          defaultValue={initial}
        />
      );
    }
    if (key === "groupIds" && Array.isArray(initial)) {
      return (
        <Controller
          key={key}
          name={key}
          render={({ field: { onChange, value } }) => (
            <SearchableSelect
              multiple
              id={key}
              label="Only show for these groups"
              options={groups}
              getOptionLabel={(group: any) => group.name}
              value={groups.filter((group: any) => value.includes(group.id))}
              onChange={(_e, data) =>
                onChange(data.map((group: any) => group.id))
              }
              filterSelectedOptions
              error={!!errors[key]}
            />
          )}
          control={control}
          defaultValue={[]}
        />
      );
    }
    return null;
  };

  return (
    <>
      <Tooltip title="Settings">
        <IconButton
          id={`${stateBranchName}SettingsIcon`}
          size="small"
          aria-label="Settings"
          onClick={handleOpen}
          sx={{ color: "text.secondary" }}
        >
          <SettingsOutlinedIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <form onSubmit={handleSubmit(formSubmit)}>
          <DialogTitle sx={{ pb: 1 }}>{title}</DialogTitle>
          <DialogContent
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 2,
              pt: "0.5rem !important",
            }}
          >
            {Object.keys(initialValues).map(renderField)}
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button primary type="submit" name={`${stateBranchName}Submit`}>
              Save
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
};

export default WidgetPrefsDialog;
