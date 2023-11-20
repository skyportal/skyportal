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
          !["groups", "owner", "obj_id", "id"].includes(key)
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
        label: "Owner",
        options: {
          customBodyRenderLite: renderOwner,
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
