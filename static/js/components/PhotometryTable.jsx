import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import Slide from "@material-ui/core/Slide";
import CloseIcon from "@material-ui/icons/Close";
import IconButton from "@material-ui/core/IconButton";
import Tooltip from "@material-ui/core/Tooltip";
import CircularProgress from "@material-ui/core/CircularProgress";

import MUIDataTable from "mui-datatables";

// eslint-disable-next-line
const Transition = React.forwardRef(function Transition(props, ref) {
  // eslint-disable-next-line
  return <Slide direction="up" ref={ref} {...props} />;
});

const isFloat = (x) =>
  typeof x === "number" && Number.isFinite(x) && Math.floor(x) !== x;

const PhotometryTable = ({ obj_id, open, onClose }) => {
  const { photometry } = useSelector((state) => state);
  let bodyContent = null;

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
      const keys = Object.keys(data[0]).filter((key) => key !== "groups");
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
        },
      }));

      const customToolbarFunc = () => (
        <>
          <Tooltip title="Close Table">
            <IconButton
              onClick={onClose}
              data-testid="close-photometry-table-button"
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
          <MUIDataTable
            title={`Photometry of ${obj_id}`}
            columns={columns}
            data={data}
            options={options}
          />
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
