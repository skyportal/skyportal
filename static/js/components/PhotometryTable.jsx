import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Slide from "@mui/material/Slide";
import CloseIcon from "@mui/icons-material/Close";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import makeStyles from "@mui/styles/makeStyles";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import CircularProgress from "@mui/material/CircularProgress";
import MUIDataTable from "mui-datatables";

import UpdatePhotometry from "./UpdatePhotometry";
import Button from "./Button";
import * as Actions from "../ducks/photometry";

const useStyles = makeStyles(() => ({
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
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

const defaultHiddenColumns = [
  "instrument_id",
  "snr",
  "magsys",
  "annotations",
  "created_at",
];

// eslint-disable-next-line
const Transition = React.forwardRef(function Transition(props, ref) {
  // eslint-disable-next-line
  return <Slide direction="up" ref={ref} {...props} />;
});

const isFloat = (x) =>
  typeof x === "number" && Number.isFinite(x) && Math.floor(x) !== x;

const PhotometryTable = ({ obj_id, open, onClose }) => {
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
          !["groups", "owner", "obj_id", "id", "streams"].includes(key)
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
          display: !defaultHiddenColumns.includes(key),
        },
      }));

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
        },
      });

      const renderStreams = (dataIndex) => {
        const phot = data[dataIndex];
        return (
          <div>
            <div className={classes.actionButtons}>
              <div>{phot.streams.map((stream) => stream.name).join(", ")}</div>
            </div>
          </div>
        );
      };

      columns.push({
        name: "streams",
        label: "streams",
        options: {
          customBodyRenderLite: renderStreams,
          display: false,
        },
      });

      const renderEdit = (dataIndex) => {
        const phot = data[dataIndex];
        return (
          <div>
            <div className={classes.actionButtons}>
              <div>
                <UpdatePhotometry phot={phot} />
              </div>
            </div>
          </div>
        );
      };
      columns.push({
        name: "edit",
        label: "Edit",
        options: {
          customBodyRenderLite: renderEdit,
        },
      });

      const renderDelete = (dataIndex) => {
        const phot = data[dataIndex];
        return (
          <div>
            <div className={classes.actionButtons}>
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
        name: "delete",
        label: "Delete",
        options: {
          customBodyRenderLite: renderDelete,
        },
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
        onDownload: (buildHead, buildBody, cols, tableData) => {
          const renderStreamsDownload = (streams) =>
            streams ? streams.map((stream) => stream.name).join(";") : "";
          const renderOwnerDownload = (owner) => (owner ? owner.username : "");

          // if there is no data, cancel download
          if (data?.length > 0) {
            const body = tableData
              .map((x) =>
                [
                  x.data[0],
                  x.data[1],
                  x.data[2],
                  x.data[3],
                  x.data[4],
                  x.data[5],
                  x.data[6],
                  x.data[7],
                  x.data[8],
                  x.data[9],
                  x.data[10],
                  x.data[11],
                  x.data[12],
                  x.data[13],
                  x.data[14],
                  x.data[15],
                  x.data[16],
                  renderOwnerDownload(x.data[18]),
                  renderStreamsDownload(x.data[19]),
                ].join(","),
              )
              .join("\n");

            const result =
              buildHead([
                {
                  name: "id",
                  download: true,
                },
                {
                  name: "mjd",
                  download: true,
                },
                {
                  name: "mag",
                  download: true,
                },
                {
                  name: "magerr",
                  download: true,
                },
                {
                  name: "limiting_mag",
                  download: true,
                },
                {
                  name: "filter",
                  download: true,
                },
                {
                  name: "instrument_name",
                  download: true,
                },
                {
                  name: "instrument_id",
                  download: true,
                },
                {
                  name: "snr",
                  download: true,
                },
                {
                  name: "magsys",
                  download: true,
                },
                {
                  name: "origin",
                  download: true,
                },
                {
                  name: "altdata",
                  download: true,
                },
                {
                  name: "ra",
                  download: true,
                },
                {
                  name: "dec",
                  download: true,
                },
                {
                  name: "ra_unc",
                  download: true,
                },
                {
                  name: "dec_unc",
                  download: true,
                },
                {
                  name: "created_at",
                  download: true,
                },
                {
                  name: "streams",
                  download: true,
                },
                {
                  name: "owner",
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
                title={`Photometry of ${obj_id}`}
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
};

export default PhotometryTable;
