import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Slide from "@mui/material/Slide";
import CloseIcon from "@mui/icons-material/Close";
import IconButton from "@mui/material/IconButton";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import QuestionMarkIcon from "@mui/icons-material/QuestionMark";
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
import UpdatePhotometry from "./UpdatePhotometry";
import PhotometryValidation from "./PhotometryValidation";
import PhotometryMagsys from "./PhotometryMagsys";
import Button from "../Button";
import * as Actions from "../../ducks/photometry";
import { mjd_to_utc } from "../../units";
import { PHOT_ZP } from "../../utils";

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

const defaultHiddenColumns = ["instrument_id", "snr", "magsys", "created_at"];

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

  const [isDeleting, setIsDeleting] = useState(null);
  const handleDelete = async (id) => {
    setIsDeleting(id);
    await dispatch(Actions.deletePhotometry(id));
    setIsDeleting(null);
  };

  const objectWithFalseValues = defaultHiddenColumns.reduce((acc, curr) => {
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

  if (!Object.keys(photometry).includes(obj_id)) {
    bodyContent = (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  } else {
    const data = photometry[obj_id];
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
      columns.push({
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
              <PhotometryValidation phot={phot} />
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
              {isDeleting === phot.id ? (
                <div>
                  <CircularProgress />
                </div>
              ) : (
                <div>
                  <Button
                    primary
                    onClick={() => {
                      handleDelete(phot.id);
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
        onDownload: (buildHead, buildBody, cols, tableData) => {
          const renderStreamsDownload = (streams) => {
            // console.log(streams);
            return streams?.length > 0
              ? streams.map((stream) => stream.name).join(";")
              : "";
          };
          const renderOwnerDownload = (owner) => (owner ? owner.username : "");

          // if there is no data, cancel download
          if (data?.length > 0) {
            const body = tableData
              .map((x) => {
                // 20 is the flux column
                // 21 is the flux error column
                // 22 is the SNR column
                // DEBUG, print each column name, value, and index
                x.data.forEach((value, index) => {
                  console.log(
                    `${
                      columns[index].name
                    } (${index}): ${value} (${typeof value})`,
                  );
                });
                x.data[17] = mjd_to_utc(x.data[1]);
                if (x.data[2] !== null) {
                  // it's a detection, we have both flux and flux error
                  x.data[20] = 10 ** (-0.4 * (x.data[2] - PHOT_ZP));
                  x.data[21] = (x.data[3] / (2.5 / Math.log(10))) * x.data[20];
                  x.data[22] = x.data[20] / x.data[21];
                  if (x.data[22] < 0 || x.data[22] === Infinity) {
                    x.data[22] = null;
                  }
                } else {
                  // it's an upper limit, we only have fluxerr
                  x.data[20] = null;
                  x.data[21] = 10 ** (-0.4 * (x.data[4] - PHOT_ZP));
                  x.data[22] = null;
                }
                return [
                  x.data[0], // id
                  x.data[1], // mjd
                  x.data[2], // mag
                  x.data[3], // magerr
                  x.data[4], // limiting_mag
                  x.data[5], // filter
                  x.data[6], // instrument_name
                  x.data[7], // instrument_id
                  // x.data[8], // snr
                  x.data[9], // magsys
                  x.data[10], // origin
                  x.data[11], // altdata
                  x.data[12], // ra
                  x.data[13], // dec
                  x.data[14], // ra_unc
                  x.data[15], // dec_unc
                  x.data[16], // created_at
                  x.data[17], // UTC date
                  renderOwnerDownload(x.data[18]),
                  renderStreamsDownload(x.data[19]),
                  x.data[20],
                  x.data[21],
                  x.data[22],
                ].join(",");
              })
              .join("\n");

            const result =
              buildHead([
                {
                  name: "id", // 0
                  download: true,
                },
                {
                  name: "mjd", // 1
                  download: true,
                },
                {
                  name: "mag", // 2
                  download: true,
                },
                {
                  name: "magerr", // 3
                  download: true,
                },
                {
                  name: "limiting_mag", // 4
                  download: true,
                },
                {
                  name: "filter", // 5
                  download: true,
                },
                {
                  name: "instrument_name", // 6
                  download: true,
                },
                {
                  name: "instrument_id", // 7
                  download: true,
                },
                {
                  name: "magsys", // 9
                  download: true,
                },
                {
                  name: "origin", // 10
                  download: true,
                },
                {
                  name: "altdata", // 11
                  download: true,
                },
                {
                  name: "ra", // 12
                  download: true,
                },
                {
                  name: "dec", // 13
                  download: true,
                },
                {
                  name: "ra_unc", // 14
                  download: true,
                },
                {
                  name: "dec_unc", // 15
                  download: true,
                },
                {
                  name: "created_at", // 16
                  download: true,
                },
                {
                  name: "UTC", // 17
                  download: true,
                },
                {
                  name: "owner", // 18
                  download: true,
                },
                {
                  name: "streams", // 19
                  download: true,
                },
                {
                  name: "flux", // 20
                  download: true,
                },
                {
                  name: "fluxerr", // 21
                  download: true,
                },
                {
                  name: "snr", // 22
                  download: true,
                },
              ]) + body;
            const blob = new Blob([result], {
              type: "text/csv;charset=utf-8;",
            });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", "photometry.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }
          return false;
        },
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
