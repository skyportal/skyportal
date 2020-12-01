import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import Slide from "@material-ui/core/Slide";
import CloseIcon from "@material-ui/icons/Close";
import IconButton from "@material-ui/core/IconButton";
import Tooltip from "@material-ui/core/Tooltip";

import MUIDataTable from "mui-datatables";

const Transition = React.forwardRef(function Transition(props, ref) {
  // eslint-disable-next-line
  return <Slide direction="up" ref={ref} {...props} />;
});

const PhotometryTable = ({ obj_id, open, onClose }) => {
  const { photometry } = useSelector((state) => state);
  let bodyContent = null;

  if (!Object.keys(photometry).includes(obj_id)) {
    bodyContent = <p>Loading...</p>;
  } else {
    const data = photometry[obj_id];
    if (data.length === 0) {
      bodyContent = <p>Source has no photometry.</p>;
    } else {
      const keys = Object.keys(data[0]).filter((key) => key !== "groups");
      const columns = keys.map((key) => ({
        name: key,
        customBodyRenderLite: (dataIndex) => {
          const value = data[dataIndex][key];
          if (typeof value === "number" && value.isInteger()) {
            return value.toString();
          }
          // use six digits after the decimal for floats
          return value.toFixed(6);
        },
      }));
      const formattedData = data.map((dataRow) =>
        keys.map((key) => dataRow[key])
      );

      const customToolbarFunc = () => {
        return (
          <>
            <Tooltip title="Close Table">
              <IconButton onClick={onClose}>
                <CloseIcon />
              </IconButton>
            </Tooltip>
          </>
        );
      };

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
            data={formattedData}
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
