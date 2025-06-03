import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DownloadIcon from "@mui/icons-material/Download";
import Typography from "@mui/material/Typography";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";

import Button from "../Button";
import { mjd_to_utc } from "../../units";
import { calculateFluxFromMag } from "../../utils/calculations";
import { PHOT_ZP } from "../../utils";
import { getValidationStatus } from "./PhotometryValidation";

const DEFAULT_DOWNLOAD_COLUMNS = [
  "id",
  "mjd",
  "mag",
  "magerr",
  "limiting_mag",
  "filter",
  "instrument_name",
  "flux",
  "fluxerr",
];

const DEFAULT_VALIDATION_FILTER = {
  validated: true,
  rejected: false,
  ambiguous: false,
  not_vetted: false,
};

const PhotometryDownload = ({
  open,
  onClose,
  data,
  objId,
  usePhotometryValidation,
  downloadParams,
  onDownload,
}) => {
  const dispatch = useDispatch();
  const [downloadFormData, setDownloadFormData] = useState({
    columns: DEFAULT_DOWNLOAD_COLUMNS,
    validationFilter: DEFAULT_VALIDATION_FILTER,
  });

  let availableDownloadColumns = [];
  if (data && data.length > 0) {
    const priorityColumns = ["id", "mjd", "mag", "magerr", "filter"];
    const allKeys = [...Object.keys(data[0]), "utc", "flux", "fluxerr"];

    const filteredKeys = allKeys.filter(
      (key) => !["groups", "obj_id", "validations"].includes(key),
    );

    // sort columns
    const priority = filteredKeys
      .filter((key) => priorityColumns.includes(key))
      .map((key) => ({ key, label: key }));

    const others = filteredKeys
      .filter((key) => !priorityColumns.includes(key))
      .sort()
      .map((key) => ({ key, label: key }));

    availableDownloadColumns = [...priority, ...others];
  }

  const downloadSchema = {
    type: "object",
    properties: {
      columns: {
        type: "array",
        title: "Columns",
        items: {
          type: "string",
          enum: availableDownloadColumns.map((col) => col.key),
          enumNames: availableDownloadColumns.map((col) => col.label),
        },
        uniqueItems: true,
        minItems: 1,
      },
    },
    required: ["columns"],
  };

  const downloadUiSchema = {
    columns: {
      "ui:widget": "checkboxes",
      "ui:options": {
        inline: true,
      },
    },
  };

  const handleValidationFilterChange = (key) => (event) => {
    setDownloadFormData((prev) => ({
      ...prev,
      validationFilter: {
        ...prev.validationFilter,
        [key]: event.target.checked,
      },
    }));
  };

  const filterDataByValidation = (tableData, filter) => {
    if (!usePhotometryValidation) return tableData;
    return tableData.filter((rowData) => {
      const phot = data[rowData.index];
      const status = getValidationStatus(phot);
      return filter[status] === true;
    });
  };

  const performDownload = (buildHead, buildBody, cols, tableData) => {
    const filteredTableData = filterDataByValidation(
      tableData,
      downloadFormData.validationFilter || DEFAULT_VALIDATION_FILTER,
    );

    if (filteredTableData?.length === 0) {
      console.warn("No data to download after filtering");
      dispatch(
        showNotification("No data to download after filtering", "error"),
      );
      return;
    }

    const body = filteredTableData
      .map((x) => {
        const phot = data[x.index];
        const { fluxValue, fluxerrValue } = calculateFluxFromMag(
          phot.mag,
          phot.magerr,
          phot.limiting_mag,
          PHOT_ZP,
        );

        const utcValue = mjd_to_utc(phot.mjd);
        const ownerData = phot.owner?.username || "";
        const streamsData =
          phot.streams?.length > 0
            ? phot.streams.map((s) => s.name).join(";")
            : "";

        return downloadFormData.columns
          .map((colKey) => {
            switch (colKey) {
              case "owner":
                return ownerData;
              case "streams":
                return streamsData;
              case "flux":
                return fluxValue;
              case "fluxerr":
                return fluxerrValue;
              case "snr":
                return phot.snr;
              case "utc":
                return utcValue;
              default:
                return phot[colKey];
            }
          })
          .join(",");
      })
      .join("\n");

    const selectedHeaders = downloadFormData.columns.map((colKey) => ({
      name: colKey,
      download: true,
    }));

    const result = buildHead(selectedHeaders) + body;
    const blob = new Blob([result], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${objId}_photometry.csv`;
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const executeDownload = () => {
    if (!downloadParams?.buildHead || !downloadParams?.tableData) {
      console.error("No download parameters available");
      return;
    }

    onClose();
    performDownload(
      downloadParams.buildHead,
      downloadParams.buildBody,
      downloadParams.cols,
      downloadParams.tableData,
    );
    onDownload();
  };

  const handleSetDefaultColumns = () => {
    setDownloadFormData((prev) => ({
      ...prev,
      columns: DEFAULT_DOWNLOAD_COLUMNS.filter((col) =>
        availableDownloadColumns.some((availCol) => availCol.key === col),
      ),
      ...(usePhotometryValidation && {
        validationFilter: DEFAULT_VALIDATION_FILTER,
      }),
    }));
  };

  const handleSetAllColumns = () => {
    setDownloadFormData((prev) => ({
      ...prev,
      columns: availableDownloadColumns.map((col) => col.key),
      ...(usePhotometryValidation && {
        validationFilter: {
          validated: true,
          rejected: true,
          ambiguous: true,
          not_vetted: true,
        },
      }),
    }));
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Typography variant="h6">Download Options</Typography>
      </DialogTitle>

      <DialogContent>
        <div style={{ marginBottom: "16px" }}>
          <Button
            size="small"
            variant="outlined"
            onClick={handleSetDefaultColumns}
            style={{ marginRight: "8px" }}
          >
            Default
          </Button>
          <Button size="small" variant="outlined" onClick={handleSetAllColumns}>
            All
          </Button>
        </div>

        <Form
          schema={downloadSchema}
          uiSchema={downloadUiSchema}
          formData={downloadFormData}
          onChange={({ formData }) => setDownloadFormData(formData)}
          validator={validator}
          showErrorList={false}
        >
          <div></div>
        </Form>

        {usePhotometryValidation && (
          <div style={{ marginTop: "16px", marginBottom: "16px" }}>
            <Typography variant="h6" style={{ marginBottom: "8px" }}>
              Validation
            </Typography>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
              }}
            >
              {Object.entries({
                validated: "Validated",
                rejected: "Rejected",
                ambiguous: "Ambiguous",
                not_vetted: "Not vetted",
              }).map(([key, label]) => (
                <FormControlLabel
                  key={key}
                  control={
                    <Checkbox
                      checked={
                        downloadFormData.validationFilter?.[key] || false
                      }
                      onChange={handleValidationFilterChange(key)}
                      size="small"
                    />
                  }
                  label={label}
                />
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: "16px" }}>
          <Button
            onClick={executeDownload}
            variant="contained"
            size="small"
            endIcon={<DownloadIcon />}
            disabled={
              !downloadFormData.columns || downloadFormData.columns.length === 0
            }
            data-testid="download-photometry-table-button"
          >
            Download
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

PhotometryDownload.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  data: PropTypes.array.isRequired,
  objId: PropTypes.string.isRequired,
  usePhotometryValidation: PropTypes.bool.isRequired,
  downloadParams: PropTypes.object,
  onDownload: PropTypes.func.isRequired,
};

PhotometryDownload.defaultProps = {
  downloadParams: null,
};

export default PhotometryDownload;
