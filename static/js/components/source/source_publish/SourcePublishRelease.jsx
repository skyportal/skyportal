import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import { fetchPublicReleases } from "../../../ducks/public_pages/public_release";
import Button from "../../Button";

const useStyles = makeStyles(() => ({
  sourcePublishOptions: {
    marginBottom: "1rem",
    display: "flex",
    flexDirection: "column",
    padding: "0 1rem",
    "& .MuiGrid-item": {
      paddingTop: "0",
    },
  },
}));

const SourcePublishRelease = ({ selectedReleaseState }) => {
  const styles = useStyles();
  const dispatch = useDispatch();
  const [releases, setReleases] = useState([]);
  const VALUE = 0;
  const SETTER = 1;

  useEffect(() => {
    dispatch(fetchPublicReleases()).then((data) => {
      setReleases(data.data);
    });
  }, [dispatch]);

  const createNewRelease = () => {};

  const formSchema = {
    type: "object",
    properties: {
      releases: {
        type: "array",
        items: {
          type: "integer",
          anyOf: releases.map((release) => ({
            enum: [release.id],
            type: "integer",
            title: release.name,
          })),
        },
        uniqueItems: true,
        default: [],
        title: "Releases to link public source page to",
      },
    },
  };
  return (
    <div className={styles.sourcePublishOptions}>
      {releases.length > 0 ? (
        <Form
          formData={selectedReleaseState[VALUE]}
          onChange={({ formData }) => selectedReleaseState[SETTER](formData)}
          schema={formSchema}
          liveValidate
          validator={validator}
          uiSchema={{
            "ui:submitButtonOptions": { norender: true },
          }}
        />
      ) : (
        <div>No releases yet, you can create the first one here</div>
      )}
      <div>
        <Button variant="contained" onClick={createNewRelease}>
          Create new release
        </Button>
      </div>
    </div>
  );
};

SourcePublishRelease.propTypes = {
  selectedReleaseState: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        }),
      ),
      PropTypes.func,
    ]),
  ).isRequired,
};

export default SourcePublishRelease;
