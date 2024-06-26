import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import { fetchPublicReleases } from "../../../ducks/public_pages/public_release";
import ReleasesList, { truncateText } from "../../release/ReleasesList";

const useStyles = makeStyles(() => ({
  sourcePublishRelease: {
    marginBottom: "1rem",
    display: "flex",
    flexDirection: "column",
    padding: "0 1rem",
    "& .MuiGrid-item": {
      paddingTop: "0",
    },
  },
  noRelease: {
    display: "flex",
    justifyContent: "center",
    padding: "1.5rem 0",
    color: "gray",
  },
  releaseItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0.5rem 1rem",
    border: "1px solid #e0e0e0",
  },
}));

const SourcePublishRelease = ({ sourceReleaseId, setSourceReleaseId }) => {
  const styles = useStyles();
  const dispatch = useDispatch();
  const [isLoading, setIsLoading] = useState(true);
  const [releases, setReleases] = useState([]);

  useEffect(() => {
    setIsLoading(true);
    dispatch(fetchPublicReleases()).then((data) => {
      setReleases(data.data.map((item) => item.PublicRelease));
      setIsLoading(false);
    });
  }, [dispatch]);

  const formSchema = {
    type: "object",
    properties: {
      release: {
        type: ["integer", "null"],
        anyOf: [
          {
            enum: [null],
            title: "--",
          },
          ...releases.map((item) => ({
            enum: [item.id],
            type: "integer",
            title: `${item.name} :  ${truncateText(item.description, 50)}`,
          })),
        ],
      },
    },
  };

  return (
    <div className={styles.sourcePublishRelease}>
      <Link
        href="/public/releases"
        target="_blank"
        style={{ fontSize: "0.7rem", textAlign: "right" }}
      >
        Public releases
      </Link>
      {releases.length > 0 ? (
        <Form
          formData={sourceReleaseId ? { release: sourceReleaseId } : undefined}
          onChange={({ formData }) => setSourceReleaseId(formData.release)}
          schema={formSchema}
          liveValidate
          validator={validator}
          uiSchema={{
            "ui:submitButtonOptions": { norender: true },
          }}
        />
      ) : (
        <div className={styles.noRelease}>
          {isLoading ? (
            <CircularProgress size={24} />
          ) : (
            <div>No releases available yet. Create the first one here.</div>
          )}
        </div>
      )}
      <ReleasesList releases={releases} setReleases={setReleases} />
    </div>
  );
};

SourcePublishRelease.propTypes = {
  sourceReleaseId: PropTypes.number,
  setSourceReleaseId: PropTypes.func.isRequired,
};

SourcePublishRelease.defaultProps = {
  sourceReleaseId: null,
};

export default SourcePublishRelease;
