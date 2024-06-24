import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import TextField from "@mui/material/TextField";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  createPublicRelease,
  deletePublicRelease,
  fetchPublicReleases,
} from "../../../ducks/public_pages/public_release";
import Button from "../../Button";

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
  noVersion: {
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

const SourcePublishRelease = ({ selectedReleaseState }) => {
  const VALUE = 0;
  const SETTER = 1;
  const styles = useStyles();
  const dispatch = useDispatch();
  const [isLoading, setIsLoading] = useState(true);
  const [releases, setReleases] = useState([]);
  const [newReleaseName, setNewReleaseName] = useState("");
  const [newReleaseDescription, setNewReleaseDescription] = useState("");
  const [openReleaseCreationForm, setOpenReleaseCreationForm] = useState(false);
  const [openReleaseList, setOpenReleaseList] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    dispatch(fetchPublicReleases()).then((data) => {
      setReleases(data.data.map((item) => item.PublicRelease));
      setIsLoading(false);
    });
  }, [dispatch]);

  const saveNewRelease = () => {
    dispatch(
      createPublicRelease({
        name: newReleaseName,
        description: newReleaseDescription,
      }),
    ).then((data) => {
      setReleases([...releases, data.data]);
      setNewReleaseName("");
      setNewReleaseDescription("");
      setOpenReleaseCreationForm(false);
    });
  };

  const deleteRelease = (id) => {
    dispatch(deletePublicRelease(id)).then((data) => {
      if (data.status === "success") {
        setReleases(releases.filter((release) => release.id !== id));
      }
    });
  };

  const truncateText = (text, length) =>
    text.length <= length ? text : `${text.substring(0, length)}...`;

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
    <div className={styles.sourcePublishRelease}>
      {releases.length > 0 ? (
        <Form
          formData={{ releases: selectedReleaseState[VALUE] }}
          onChange={({ formData }) =>
            selectedReleaseState[SETTER](formData.releases)
          }
          schema={formSchema}
          liveValidate
          validator={validator}
          uiSchema={{
            "ui:submitButtonOptions": { norender: true },
          }}
        />
      ) : (
        <div className={styles.noVersion}>
          {isLoading ? (
            <CircularProgress size={24} />
          ) : (
            <div>No releases available yet. Create the first one here.</div>
          )}
        </div>
      )}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "0.4rem",
        }}
      >
        <Button
          onClick={() => {
            setOpenReleaseList(!openReleaseList);
            setOpenReleaseCreationForm(false);
          }}
        >
          Edit releases {openReleaseList ? <ExpandLess /> : <ExpandMore />}
        </Button>
        <Button
          onClick={() => {
            setOpenReleaseCreationForm(!openReleaseCreationForm);
            setOpenReleaseList(false);
          }}
        >
          <AddIcon />
        </Button>
      </div>
      {openReleaseList &&
        releases.map((release) => (
          <div key={`release_${release.id}`} className={styles.releaseItem}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div style={{ fontWeight: "bold", marginBottom: "1rem" }}>
                {release.name}
              </div>
              <div>{truncateText(release.description, 40)}</div>
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <Button
                onClick={() => {
                  deleteRelease(release.id);
                }}
              >
                <EditIcon />
              </Button>
              <Button
                onClick={() => {
                  deleteRelease(release.id);
                }}
              >
                <DeleteIcon />
              </Button>
            </div>
          </div>
        ))}
      {openReleaseCreationForm && (
        <div
          style={{
            marginTop: "1rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            rowGap: "1rem",
          }}
        >
          <TextField
            data-testid="updateSummaryTextfield"
            size="small"
            label="release name"
            value={newReleaseName}
            name="releaseName"
            minRows={1}
            fullWidth
            multiline
            onChange={(data) => setNewReleaseName(data.target.value)}
            variant="outlined"
          />
          <TextField
            data-testid="updateSummaryTextfield"
            size="small"
            label="release description"
            value={newReleaseDescription}
            name="description"
            minRows={3}
            fullWidth
            multiline
            onChange={(data) => setNewReleaseDescription(data.target.value)}
            variant="outlined"
          />
          <Button
            secondary
            onClick={() => {
              saveNewRelease();
            }}
            endIcon={<SaveIcon />}
            size="large"
            data-testid="createReleaseSubmitButton"
            disabled={newReleaseName === ""}
          >
            Save
          </Button>
        </div>
      )}
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
