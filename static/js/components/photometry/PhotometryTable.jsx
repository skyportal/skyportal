import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Slide from "@mui/material/Slide";
import CloseIcon from "@mui/icons-material/Close";
import IconButton from "@mui/material/IconButton";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import QuestionMarkIcon from "@mui/icons-material/QuestionMark";
import DownloadIcon from "@mui/icons-material/Download";
import PriorityHigh from "@mui/icons-material/PriorityHigh";
import Tooltip from "@mui/material/Tooltip";
import makeStyles from "@mui/styles/makeStyles";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import CircularProgress from "@mui/material/CircularProgress";
import MUIDataTable from "mui-datatables";
import Typography from "@mui/material/Typography";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import UpdatePhotometry from "./UpdatePhotometry";
import PhotometryValidation, {
  getValidationStatus,
} from "./PhotometryValidation";
import PhotometryMagsys from "./PhotometryMagsys";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import Button from "../Button";
import * as Actions from "../../ducks/photometry";
import { mjd_to_utc } from "../../units";
import { PHOT_ZP } from "../../utils";

const DEFAULT_DOWNLOAD_COLUMNS = [
  "id",
  "mjd",
  "mag",
  "magerr",
  "limiting_mag",
  "filter",
  "instrument_name",
];
const DEFAULT_HIDDEN_COLUMNS = [
  "instrument_id",
  "ra",
  "dec",
  "ra_unc",
  "dec_unc",
  "created_at",
];

const calculateFluxFromMag = (mag, magerr, limitingMag) => {
  let fluxValue = null;
  let fluxerrValue = null;

  if (mag !== null) {
    // it's a detection, we have both flux and flux error
    fluxValue = 10 ** (-0.4 * (mag - PHOT_ZP));
    if (magerr !== null) {
      fluxerrValue = (magerr / (2.5 / Math.log(10))) * fluxValue;
    }
  } else {
    // it's an upper limit, we only have fluxerr
    fluxerrValue = 10 ** (-0.4 * (limitingMag - PHOT_ZP));
  }

  return { fluxValue, fluxerrValue };
};

const useStyles = makeStyles(() => ({
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
  },
  manage: {
    display: "flex",
    flexDirection: "row",
    gap: "0.2rem",
    marginRight: "0.4rem",
  },
}));

const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUITableCell: {
        styleOverrides: {
          paddingCheckbox: {
            padding: 0,
            margin: 0,
          },
        },
      },
      MUIDataTableBodyCell: {
        styleOverrides: {
          root: {
            padding: "0.25rem",
            paddingRight: 0,
            margin: 0,
          },
        },
      },
      MUIDataTableHeadCell: {
        styleOverrides: {
          root: {
            padding: "0.5rem",
            paddingRight: 0,
            margin: 0,
          },
          sortLabelRoot: {
            height: "1.4rem",
          },
        },
      },
    },
  });

const Transition = React.forwardRef(function Transition(props, ref) {
  return <Slide direction="up" ref={ref} {...props} />;
});

const isFloat = (x) =>
  typeof x === "number" && Number.isFinite(x) && Math.floor(x) !== x;

const PhotometryTable = ({ obj_id, open, onClose, magsys, setMagsys }) => {
  const { usePhotometryValidation } = useSelector((state) => state.config);
  const photometry = useSelector((state) => state.photometry);
  let bodyContent = null;

  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [downloadOptionsOpen, setDownloadOptionsOpen] = useState(false);
  const [downloadFormData, setDownloadFormData] = useState({
    columns: DEFAULT_DOWNLOAD_COLUMNS,
    validationFilter: {
      validated: true,
      rejected: false,
      ambiguous: false,
      not_vetted: true,
    },
  });

  const [downloadParams, setDownloadParams] = useState(null);

  const data = photometry[obj_id] || [];

  let availableDownloadColumns = [];
  if (data && data.length > 0) {
    const priorityColumns = ["id", "mjd", "mag", "magerr", "filter"];
    const allKeys = [...Object.keys(data[0]), "utc", "flux", "fluxerr"];

    const filteredKeys = allKeys.filter(
      (key) => !["groups", "obj_id", "validations"].includes(key),
    );

    // sort colomns
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
  if (usePhotometryValidation) {
    downloadSchema.properties.validationFilter = {
      type: "object",
      title: "Validation",
      properties: {
        validated: { type: "boolean", default: true },
        rejected: { type: "boolean", default: false },
        ambiguous: { type: "boolean", default: false },
        not_vetted: { type: "boolean", default: true },
      },
    };
  }

  const handleDelete = async () => {
    if (!deleteDialogOpen) {
      return;
    }
    await dispatch(Actions.deletePhotometry(deleteDialogOpen));
    setDeleteDialogOpen(false);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
  };

  const objectWithFalseValues = DEFAULT_HIDDEN_COLUMNS.reduce((acc, curr) => {
    acc[curr] = false;
    return acc;
  }, {});

  const [openColumns, setOpenColumns] = useState(objectWithFalseValues);
  const handleColumnViewChange = (columnName, action) => {
    setOpenColumns((prevOpenColumns) => ({
      ...prevOpenColumns,
      [columnName]: action === "add",
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
      downloadFormData.validationFilter || {
        validated: true,
        rejected: false,
        ambiguous: false,
        not_vetted: true,
      },
    );

    if (filteredTableData?.length === 0) {
      console.warn("No data to download after filtering");
      return;
    }

    const body = filteredTableData
      .map((x) => {
        const phot = data[x.index];
        const { fluxValue, fluxerrValue } = calculateFluxFromMag(
          phot.mag,
          phot.magerr,
          phot.limiting_mag,
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
    link.download = `${obj_id}_photometry.csv`;
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownload = (buildHead, buildBody, cols, tableData) => {
    setDownloadParams({ buildHead, buildBody, cols, tableData });
    setDownloadOptionsOpen(true);
    return false;
  };

  const executeDownload = () => {
    if (!downloadParams?.buildHead || !downloadParams?.tableData) {
      console.error("No download parameters available");
      return;
    }

    setDownloadOptionsOpen(false);
    performDownload(
      downloadParams.buildHead,
      downloadParams.buildBody,
      downloadParams.cols,
      downloadParams.tableData,
    );
    setDownloadParams(null);
  };

  if (!Object.keys(photometry).includes(obj_id)) {
    bodyContent = (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  } else {
    if (data.length === 0) {
      bodyContent = <p>Source has no photometry.</p>;
    } else {
      const keys = [
        "id",
        "mjd",
        "mag",
        "magerr",
        "limiting_mag",
        "filter",
        "instrument_name",
        "instrument_id",
        "snr",
        "magsys",
        "origin",
        "altdata",
        "ra",
        "dec",
        "ra_unc",
        "dec_unc",
        "created_at",
      ];
      Object.keys(data[0]).forEach((key) => {
        if (
          !keys.includes(key) &&
          ![
            "groups",
            "owner",
            "obj_id",
            "id",
            "streams",
            "validations",
          ].includes(key)
        ) {
          keys.push(key);
        }
      });
      const downloadUiSchema = {
        columns: {
          "ui:widget": "checkboxes",
          "ui:options": {
            inline: true,
          },
        },
      };

      const columns = keys.map((key) => ({
        name: key,
        options: {
          customBodyRenderLite: (dataIndex) => {
            const value = data[dataIndex][key];
            if (isFloat(value)) {
              return value.toFixed(key.includes("jd") ? 8 : 6);
            }
            if (
              key === "altdata" &&
              typeof value === "object" &&
              value !== null
            ) {
              return JSON.stringify(value);
            }
            return value;
          },
          display: openColumns[key] === false ? "false" : "true",
        },
      }));

      const renderUTC = (dataIndex) => {
        const phot = data[dataIndex];
        return (
          <div>
            <div className={classes.actionButtons}>
              <div>{mjd_to_utc(phot.mjd)}</div>
            </div>
          </div>
        );
      };
      const mjdIndex = columns.findIndex((col) => col.name === "mjd");
      columns.splice(mjdIndex + 1, 0, {
        name: "UTC",
        label: "UTC",
        options: {
          customBodyRenderLite: renderUTC,
          display: openColumns.UTC === false ? "false" : "true",
        },
      });

      const renderOwner = (dataIndex) => {
        const phot = data[dataIndex];
        return (
          <div>
            <div className={classes.actionButtons}>
              <div>{phot.owner.username}</div>
            </div>
          </div>
        );
      };
      columns.push({
        name: "owner",
        label: "owner",
        options: {
          customBodyRenderLite: renderOwner,
          display: openColumns.owner === false ? "false" : "true",
        },
      });

      const renderStreams = (dataIndex) => {
        const phot = data[dataIndex];
        return (
          <div>
            <div className={classes.actionButtons}>
              <div>
                {(phot.streams || []).map((stream) => stream.name).join(", ")}
              </div>
            </div>
          </div>
        );
      };

      columns.push({
        name: "streams",
        label: "streams",
        options: {
          customBodyRenderLite: renderStreams,
          display: openColumns.streams === false ? "false" : "true",
        },
      });

      if (usePhotometryValidation) {
        const renderValidationStatus = (dataIndex) => {
          const phot = data[dataIndex];
          let statusIcon = null;
          if (phot?.validations.length === 0) {
            statusIcon = <PriorityHigh size="small" color="primary" />;
          } else if (phot?.validations[0]?.validated === true) {
            statusIcon = <CheckIcon size="small" color="green" />;
          } else if (phot?.validations[0]?.validated === false) {
            statusIcon = <ClearIcon size="small" color="secondary" />;
          } else {
            statusIcon = <QuestionMarkIcon size="small" color="primary" />;
          }

          return (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                justifyContent: "center",
              }}
              name={`${phot.id}_validation_status`}
            >
              {statusIcon}
              <PhotometryValidation phot={phot} magsys={magsys} />
            </div>
          );
        };

        columns.push({
          name: "validation_status",
          label: "Validation",
          options: {
            customBodyRenderLite: renderValidationStatus,
            display: openColumns.validation_status === false ? "false" : "true",
          },
        });

        const renderValidationExplanation = (dataIndex) => {
          const phot = data[dataIndex];
          let validationExplanation = null;
          if (phot?.validations.length === 0) {
            validationExplanation = "";
          } else {
            validationExplanation = phot?.validations[0]?.explanation;
          }
          return (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                justifyContent: "center",
              }}
              name={`${phot.id}_validation_explanation`}
            >
              {validationExplanation}
            </div>
          );
        };

        columns.push({
          name: "validation_explanation",
          label: "Explanation",
          options: {
            customBodyRenderLite: renderValidationExplanation,
            display:
              openColumns.validation_explanation === false ? "false" : "true",
          },
        });

        const renderValidationNotes = (dataIndex) => {
          const phot = data[dataIndex];
          let notes = null;
          if (phot?.validations.length === 0) {
            notes = "";
          } else {
            notes = phot?.validations[0]?.notes;
          }
          return (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                justifyContent: "center",
              }}
              name={`${phot.id}_validation_notes`}
            >
              {notes}
            </div>
          );
        };

        columns.push({
          name: "validation_notes",
          label: "Notes",
          options: {
            customBodyRenderLite: renderValidationNotes,
            display: openColumns.validation_notes === false ? "false" : "true",
          },
        });
      }

      const renderManage = (dataIndex) => {
        const phot = data[dataIndex];
        return (
          <div>
            <div className={classes.manage}>
              <div>
                <UpdatePhotometry phot={phot} magsys={magsys} />
              </div>
              {deleteDialogOpen === phot.id ? (
                <div>
                  <CircularProgress />
                </div>
              ) : (
                <div>
                  <Button
                    primary
                    onClick={() => {
                      setDeleteDialogOpen(phot.id);
                    }}
                    size="small"
                    type="submit"
                    data-testid={`deleteRequest_${photometry.id}`}
                  >
                    Delete
                  </Button>
                </div>
              )}
            </div>
          </div>
        );
      };
      columns.push({
        name: "manage",
        label: "Manage",
        options: {
          customBodyRenderLite: renderManage,
        },
        display: openColumns.manage === false ? "false" : "true",
      });

      const customToolbarFunc = () => (
        <>
          <Tooltip title="Close Table">
            <IconButton
              onClick={onClose}
              data-testid="close-photometry-table-button"
              size="large"
            >
              <CloseIcon />
            </IconButton>
          </Tooltip>
        </>
      );

      const options = {
        draggableColumns: { enabled: false },
        expandableRows: false,
        selectableRows: "none",
        customToolbar: customToolbarFunc,
        filter: false,
        download: true,
        onColumnViewChange: handleColumnViewChange,
        onDownload: handleDownload,
      };

      bodyContent = (
        <div>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title={
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      flexDirection: "row",
                      gap: "1rem",
                    }}
                  >
                    <Typography variant="h6" noWrap>
                      {`Photometry of ${obj_id}`}
                    </Typography>
                    {magsys && typeof setMagsys === "function" && (
                      <PhotometryMagsys magsys={magsys} setMagsys={setMagsys} />
                    )}
                  </div>
                }
                columns={columns}
                data={data}
                options={options}
              />
            </ThemeProvider>
          </StyledEngineProvider>
          <ConfirmDeletionDialog
            deleteFunction={handleDelete}
            dialogOpen={deleteDialogOpen}
            closeDialog={closeDeleteDialog}
            resourceName="Photometry Point"
          />
          <Dialog
            open={downloadOptionsOpen}
            onClose={() => setDownloadOptionsOpen(false)}
            maxWidth="xs"
            fullWidth
          >
            <DialogTitle>
              <Typography variant="h6">Download Options</Typography>
            </DialogTitle>

            <DialogContent>
              <div>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() =>
                    setDownloadFormData((prev) => ({
                      ...prev,
                      columns: DEFAULT_DOWNLOAD_COLUMNS.filter((col) =>
                        availableDownloadColumns.some(
                          (availCol) => availCol.key === col,
                        ),
                      ),
                    }))
                  }
                >
                  Default
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() =>
                    setDownloadFormData((prev) => ({
                      ...prev,
                      columns: availableDownloadColumns.map((col) => col.key),
                    }))
                  }
                >
                  All
                </Button>
              </div>

              <div>
                <Form
                  schema={downloadSchema}
                  uiSchema={downloadUiSchema}
                  formData={downloadFormData}
                  onChange={({ formData }) => setDownloadFormData(formData)}
                  onSubmit={executeDownload}
                  validator={validator}
                  showErrorList={false}
                >
                  <Button
                    type="submit"
                    variant="contained"
                    size="small"
                    endIcon={<DownloadIcon />}
                    disabled={
                      !downloadFormData.columns ||
                      downloadFormData.columns.length === 0
                    }
                    data-testid="download-photometry-table-button"
                  >
                    Download
                  </Button>
                </Form>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      );
    }
  }
  return (
    <Dialog
      fullScreen
      open={open}
      onClose={onClose}
      TransitionComponent={Transition}
    >
      <DialogContent>{bodyContent}</DialogContent>
    </Dialog>
  );
};

PhotometryTable.propTypes = {
  obj_id: PropTypes.string.isRequired,
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  magsys: PropTypes.string,
  setMagsys: PropTypes.func,
};

PhotometryTable.defaultProps = {
  magsys: null,
  setMagsys: null,
};

export default PhotometryTable;
