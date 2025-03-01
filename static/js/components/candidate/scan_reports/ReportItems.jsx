import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import EditIcon from "@mui/icons-material/Edit";
import { Link } from "react-router-dom";
import EditReportItemForm from "./EditReportItemForm";
import { fetchScanReportItem } from "../../../ducks/candidate/scan_report";
import IconButton from "@mui/material/IconButton";

const List = styled("div")({
  display: "flex",
  flexDirection: "column",
});

const Item = styled("div")({
  display: "flex",
  textAlign: "center",
  paddingBottom: "0.8rem",
  marginBottom: "0.8rem",
});

const Field = styled("div")({
  flex: 1,
  borderRight: "1px solid #d3d3d3",
  fontSize: "0.8rem",
  display: "flex",
  flexDirection: "column",
  rowGap: "0.4rem",
  justifyContent: "center",
  alignItems: "center",
  padding: "0.1rem 0.2rem",
  minWidth: "120px",
});

const FieldTitle = styled(Field)({
  borderColor: "grey",
});

const ReportItem = ({ reportId, isMultiGroup }) => {
  const dispatch = useDispatch();
  const reportItems = useSelector((state) => state.scanReportItems);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [itemToEdit, setItemToEdit] = useState(null);

  useEffect(() => {
    setLoading(true);
    dispatch(fetchScanReportItem(reportId)).then(() => setLoading(false));
  }, [dispatch, reportId]);

  const displayDate = (date) => {
    return new Date(date).toLocaleDateString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
    });
  };

  return (
    <Box>
      <Paper sx={{ padding: "1rem", overflowX: "scroll" }}>
        <List>
          <Item
            sx={{
              fontWeight: "bold",
              borderBottom: "1px solid grey",
            }}
          >
            <FieldTitle>date</FieldTitle>
            <FieldTitle>scanner</FieldTitle>
            {isMultiGroup && <FieldTitle>group</FieldTitle>}
            <FieldTitle sx={{ flex: 2 }}>ZTF Name Fritz link</FieldTitle>
            <FieldTitle sx={{ flex: 2 }}>comment</FieldTitle>
            <FieldTitle sx={{ flex: 2 }}>classifications</FieldTitle>
            <FieldTitle>host redshift</FieldTitle>
            <FieldTitle>current mag</FieldTitle>
            <FieldTitle>current age</FieldTitle>
            <FieldTitle sx={{ borderRight: "none" }}></FieldTitle>
          </Item>
          {!loading && reportItems.length ? (
            reportItems.map((reportItem) => (
              <Item
                key={reportItem.id}
                sx={{ borderBottom: "1px solid #d3d3d3" }}
              >
                <Field>
                  {reportItem.data.saved_infos.map((info, index) => (
                    <div key={index}>{displayDate(info.saved_at)}</div>
                  ))}
                </Field>
                <Field>
                  {reportItem.data.saved_infos.map((info, index) => (
                    <div key={index}>{info.saved_by}</div>
                  ))}
                </Field>
                {isMultiGroup && (
                  <Field>
                    {reportItem.data.saved_infos.map((info, index) => (
                      <Chip
                        label={info.group.substring(0, 15)}
                        size="small"
                        key={index}
                      />
                    ))}
                  </Field>
                )}
                <Field sx={{ flex: 2 }}>
                  <Link
                    to={`/source/${reportItem.obj_id}`}
                    role="link"
                    target="_blank"
                  >
                    {reportItem.obj_id}
                  </Link>
                </Field>
                <Field sx={{ flex: 2 }}>{reportItem.data.comment}</Field>
                <Field sx={{ flex: 2 }}>
                  {reportItem.data.classifications?.map(
                    (classification, index) => (
                      <Chip
                        label={
                          (classification.ml ? "ML: " : "") +
                          classification.classification +
                          (classification.probability < 0.1 ? "?" : "")
                        }
                        size="small"
                        key={index}
                      />
                    ),
                  )}
                </Field>
                <Field>{reportItem.data.host_redshift}</Field>
                <Field>{reportItem.data.current_mag}</Field>
                <Field>{reportItem.data.current_age}</Field>
                <Field sx={{ borderRight: "none" }}>
                  <Button
                    onClick={() => {
                      setItemToEdit(reportItem);
                      setDialogOpen(true);
                    }}
                  >
                    <EditIcon color="primary" fontSize="small" />
                  </Button>
                </Field>
              </Item>
            ))
          ) : (
            <Item
              sx={{
                display: "flex",
                justifyContent: "center",
                paddingTop: "1rem",
              }}
            >
              {loading && <CircularProgress size={24} />}
            </Item>
          )}
        </List>
      </Paper>
      {itemToEdit && (
        <EditReportItemForm
          dialogOpen={dialogOpen}
          setDialogOpen={setDialogOpen}
          reportId={reportId}
          itemToEdit={itemToEdit}
          setItemToEdit={setItemToEdit}
        />
      )}
    </Box>
  );
};

ReportItem.propTypes = {
  reportId: PropTypes.number.isRequired,
  isMultiGroup: PropTypes.bool.isRequired,
};

export default ReportItem;
