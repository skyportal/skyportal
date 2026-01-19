import React, { useState, useEffect } from "react";
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

const DEFAULT_COLUMN_ORDER = [
  "id",
  "mjd",
  "utc",
  "mag",
  "magerr",
  "mag_corr",
  "extinction",
  "limiting_mag",
  "filter",
  "snr",
  "magsys",
  "instrument_name",
  "instrument_id",
  "origin",
  "flux",
  "fluxerr",
  "flux_corr",
  "ra",
  "dec",
  "ra_unc",
  "dec_unc",
  "created_at",
  "altdata",
  "streams",
];

const DEFAULT_COLUMNS = [
  "id",
  "mjd",
  "mag",
  "magerr",
  "mag_corr",
  "extinction",
  "limiting_mag",
  "filter",
  "instrument_name",
  "flux",
  "fluxerr",
  "flux_corr",
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
    columns: [],
    filters: [],
    validationFilter: DEFAULT_VALIDATION_FILTER,
  });
  const [downloadMode, setDownloadMode] = useState("default");

  const orderColumns = (columns) => {
    const orderedColumns = DEFAULT_COLUMN_ORDER.filter((col) =>
      columns.includes(col),
    );
    const remainingColumns = columns.filter(
      (col) => !DEFAULT_COLUMN_ORDER.includes(col),
    );
    return [...orderedColumns, ...remainingColumns];
  };

  let availableDownloadColumns = [];
  let availableFilters = [];
  if (data && data.length > 0) {
    const allKeys = [...Object.keys(data[0]), "utc", "flux", "fluxerr"];
    const filteredKeys = allKeys.filter(
      (key) => !["groups", "obj_id", "validations"].includes(key),
    );

    const orderedKeys = orderColumns(filteredKeys);
    availableDownloadColumns = orderedKeys.map((key) => ({ key, label: key }));

    const filtersSet = new Set();
    data.forEach((phot) => {
      if (phot.filter) {
        filtersSet.add(phot.filter);
      }
    });
    availableFilters = Array.from(filtersSet).sort();
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
      filters: {
        type: "array",
        title: "Filters",
        items: {
          type: "string",
          enum: availableFilters,
        },
        uniqueItems: true,
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
    filters: {
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

  const setColumnsForMode = (mode) => {
    setDownloadMode(mode);

    let selectedColumns;
    let validationFilter = DEFAULT_VALIDATION_FILTER;

    switch (mode) {
      case "default":
        selectedColumns = DEFAULT_COLUMNS.filter((col) =>
          availableDownloadColumns.some((availCol) => availCol.key === col),
        );
        break;
      case "all":
        selectedColumns = availableDownloadColumns.map((col) => col.key);
        validationFilter = {
          validated: true,
          rejected: true,
          ambiguous: true,
          not_vetted: true,
        };
        break;
      default:
        selectedColumns = [];
    }

    const orderedColumns = orderColumns(selectedColumns);

    setDownloadFormData((prev) => ({
      ...prev,
      columns: orderedColumns,
      filters: availableFilters,
      ...(usePhotometryValidation && { validationFilter }),
    }));
  };

  const handleSetDefaultColumns = () => setColumnsForMode("default");
  const handleSetAllColumns = () => setColumnsForMode("all");

  useEffect(() => {
    if (
      availableDownloadColumns.length > 0 &&
      downloadFormData.columns.length === 0
    ) {
      setColumnsForMode("default");
    }
  }, [availableDownloadColumns]);

  const performDownload = (buildHead, buildBody, cols, tableData) => {
    let filteredTableData = filterDataByValidation(
      tableData,
      downloadFormData.validationFilter || DEFAULT_VALIDATION_FILTER,
    );

    if (downloadFormData.filters && downloadFormData.filters.length > 0) {
      filteredTableData = filteredTableData.filter((rowData) => {
        const phot = data[rowData.index];
        const result = downloadFormData.filters.includes(phot.filter);
        return result;
      });
    }

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
              case "extinction":
                return phot.extinction;
              case "mag_corr":
                return phot.mag_corr;
              case "flux_corr":
                return phot.flux_corr;
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

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Typography variant="h6">Download Options</Typography>
      </DialogTitle>

      <DialogContent>
        <div style={{ marginBottom: "16px" }}>
          <Button
            size="small"
            variant={downloadMode === "default" ? "contained" : "outlined"}
            onClick={handleSetDefaultColumns}
            style={{ marginRight: "8px" }}
          >
            Default
          </Button>
          <Button
            size="small"
            variant={downloadMode === "all" ? "contained" : "outlined"}
            onClick={handleSetAllColumns}
          >
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
