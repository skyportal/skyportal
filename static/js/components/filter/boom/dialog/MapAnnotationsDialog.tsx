import { useEffect } from "react";
import {
  Button,
  Box,
  Typography,
  Paper,
  IconButton,
  FormControl,
  Select,
  MenuItem,
  TextField,
  Autocomplete,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import { Add as AddIcon, Delete as DeleteIcon } from "@mui/icons-material";
import CloseIcon from "@mui/icons-material/Close";

const getOutputFieldName = (arrayField: any) => {
  return arrayField?.outputName
    ? `${arrayField.outputName}`
    : `${arrayField.fieldName}_mapped`;
};

const getMongoMapQuery = (arrayField: any, mapProjectionFields: any[]) => {
  if (!arrayField || !arrayField.fieldName || mapProjectionFields.length === 0)
    return null;
  const inObj: Record<string, any> = {};
  mapProjectionFields.forEach((f: any) => {
    if (!f.outputName || !f.fieldName) return;
    let value;
    switch (f.type) {
      case "exclude":
        value = 0;
        break;
      case "round":
        value = {
          $round: [
            `$$match.${f.fieldName.label}`,
            typeof f.roundDecimals === "number" ? f.roundDecimals : 4,
          ],
        };
        break;
      case "include":
      default:
        value = `$$match.${f.fieldName.label}`;
    }
    inObj[f.outputName] = value;
  });
  return {
    $map: {
      input: `$${arrayField.fieldName}`,
      as: "match",
      in: inObj,
    },
  };
};

interface MapAnnotationsDialogProps {
  open: boolean;
  onClose: (...a: any[]) => void;
  arrayField?: any;
  mapProjectionFields: any[];
  setMapProjectionFields: (...a: any[]) => void;
  onSave: (...a: any[]) => void;
}

const MapAnnotationsDialog = ({
  open,
  onClose,
  arrayField,
  mapProjectionFields,
  setMapProjectionFields,
  onSave,
}: MapAnnotationsDialogProps) => {
  // Ensure there's always at least one empty field when dialog opens
  useEffect(() => {
    if (open && mapProjectionFields.length === 0) {
      setMapProjectionFields([
        {
          id: Date.now(),
          fieldName: "",
          outputName: "",
          type: "include",
        },
      ]);
    }
  }, [open, mapProjectionFields.length, setMapProjectionFields]);

  const subFields: any[] = arrayField?.subFields || [];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Map Annotations to Array Field
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {arrayField && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2">Selected Array Field:</Typography>
            <Typography variant="body1" sx={{ fontWeight: 500, mb: 1 }}>
              {arrayField.fieldName}
            </Typography>
          </Box>
        )}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {mapProjectionFields.map((mapField: any, idx: number) => (
            <Paper key={mapField.id || idx} variant="outlined" sx={{ p: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  flexWrap: "wrap",
                }}
              >
                <TextField
                  label="Annotation Name"
                  value={mapField.outputName}
                  onChange={(e: any) =>
                    setMapProjectionFields((fields: any[]) =>
                      fields.map((f: any) =>
                        f.id === mapField.id
                          ? { ...f, outputName: e.target.value }
                          : f,
                      ),
                    )
                  }
                  size="small"
                  sx={{ minWidth: 150 }}
                  placeholder={mapField.fieldName}
                />
                <Autocomplete
                  value={
                    mapField.fieldName
                      ? subFields
                          .map((sf: any) => ({ label: sf, name: sf }))
                          .find(
                            (opt: any) => opt.name === mapField.fieldName,
                          ) || null
                      : null
                  }
                  onChange={(_: any, newValue: any) => {
                    setMapProjectionFields((fields: any[]) =>
                      fields.map((f: any) =>
                        f.id === mapField.id
                          ? {
                              ...f,
                              fieldName:
                                typeof newValue === "string"
                                  ? newValue
                                  : newValue?.name || newValue?.label || "",
                            }
                          : f,
                      ),
                    );
                  }}
                  options={subFields.map((sf: any) => ({
                    label: sf,
                    name: sf,
                  }))}
                  isOptionEqualToValue={(option: any, value: any) =>
                    option.name === value?.name
                  }
                  getOptionLabel={(option: any) => {
                    if (
                      typeof option.label === "object" &&
                      option.label !== null
                    ) {
                      return option.label.label || "";
                    }
                    if (
                      typeof option.name === "object" &&
                      option.name !== null
                    ) {
                      return option.name.label || "";
                    }
                    return option.label || option.name || "";
                  }}
                  sx={{ minWidth: 250 }}
                  renderInput={(params: any) => (
                    <TextField
                      {...params}
                      label="Field (subfield)"
                      size="small"
                    />
                  )}
                  renderOption={(props: any, option: any) => {
                    const { key, ...otherProps } = props;
                    return (
                      <li key={option.name || option.label} {...otherProps}>
                        {option.label || option.name || ""}
                      </li>
                    );
                  }}
                />
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>Type</InputLabel>
                  <Select
                    value={mapField.type || "include"}
                    onChange={(e: any) =>
                      setMapProjectionFields((fields: any[]) =>
                        fields.map((f: any) =>
                          f.id === mapField.id
                            ? { ...f, type: e.target.value }
                            : f,
                        ),
                      )
                    }
                    label="Type"
                  >
                    <MenuItem value="include">Include</MenuItem>
                    <MenuItem value="exclude">Exclude</MenuItem>
                    <MenuItem value="round">Round</MenuItem>
                  </Select>
                </FormControl>
                {mapField.type === "round" && (
                  <TextField
                    label="Decimals"
                    type="number"
                    value={
                      typeof mapField.roundDecimals === "number"
                        ? mapField.roundDecimals
                        : 4
                    }
                    onChange={(e: any) => {
                      const val = Math.max(
                        0,
                        Math.min(10, parseInt(e.target.value) || 0),
                      );
                      setMapProjectionFields((fields: any[]) =>
                        fields.map((f: any) =>
                          f.id === mapField.id
                            ? { ...f, roundDecimals: val }
                            : f,
                        ),
                      );
                    }}
                    size="small"
                    sx={{ width: 100 }}
                    slotProps={{ htmlInput: { min: 0, max: 10 } }}
                  />
                )}
                <IconButton
                  onClick={() =>
                    setMapProjectionFields((fields: any[]) =>
                      fields.filter((f: any) => f.id !== mapField.id),
                    )
                  }
                  color="error"
                  size="small"
                >
                  <DeleteIcon />
                </IconButton>
              </Box>
            </Paper>
          ))}
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            size="small"
            onClick={() =>
              setMapProjectionFields((fields: any[]) => [
                ...fields,
                { id: Date.now(), fieldName: "", outputName: "" },
              ])
            }
          >
            Add Map Annotation
          </Button>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button
          variant="contained"
          color="primary"
          onClick={() => {
            if (onSave) {
              const mongoMapQuery = getMongoMapQuery(
                arrayField,
                mapProjectionFields,
              );
              const outputFieldName = getOutputFieldName(arrayField);
              onSave({ outputFieldName, mongoMapQuery });
            }
            onClose();
          }}
        >
          Save
        </Button>
        <Button onClick={onClose} color="primary">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MapAnnotationsDialog;
