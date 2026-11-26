import { useGetProfileQuery } from "../../../ducks/profile";
import { useState } from "react";
import Tooltip from "@mui/material/Tooltip";
import DialogContent from "@mui/material/DialogContent";
import Box from "@mui/material/Box";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import CircularProgress from "@mui/material/CircularProgress";
import { useGeneratePublicSourcePageMutation } from "../../../ducks/public_pages/public_source_page";
import Button from "../../Button";
import SourcePublishOptions from "./SourcePublishOptions";
import SourcePublishHistory from "./SourcePublishHistory";
import SourcePublishRelease from "./SourcePublishRelease";

const expandButtonSx = {
  bgcolor: "#80808017",
  width: "100%",
  display: "flex",
  justifyContent: "space-between",
  color: "gray",
  fontSize: "1rem",
  borderBottom: "2px solid #e0e0e0",
  borderRadius: 0,
  mb: 1,
};

interface SourcePublishProps {
  sourceId: string;
  isElements: {
    summary?: boolean;
    photometry?: boolean;
    spectroscopy?: boolean;
    classifications?: boolean;
  };
}

const SourcePublish = ({ sourceId, isElements }: SourcePublishProps) => {
  const [generatePublicSourcePage] = useGeneratePublicSourcePageMutation();
  const { data: currentUser } = useGetProfileQuery();
  const manageSourcesAccess =
    currentUser?.permissions?.includes("Manage sources");
  const displayOptions =
    manageSourcesAccess &&
    (isElements.summary ||
      isElements.photometry ||
      isElements.spectroscopy ||
      isElements.classifications);

  const [publishButton, setPublishButton] = useState({
    text: "Publish",
    color: "",
  });
  const [sourcePublishReleaseOpen, setSourcePublishReleaseOpen] =
    useState(true);
  const [sourcePublishOptionsOpen, setSourcePublishOptionsOpen] =
    useState(false);
  const [sourcePublishHistoryOpen, setSourcePublishHistoryOpen] =
    useState(true);
  const [sourceReleaseId, setSourceReleaseId] = useState<any>(null);
  const [options, setOptions] = useState<Record<string, any>>({
    include_summary: true,
    include_photometry: true,
    include_spectroscopy: true,
    include_classifications: true,
    groups: [],
    streams: [],
  });
  const publish = async () => {
    if (manageSourcesAccess) {
      setPublishButton({ text: "loading", color: "" });
      try {
        await generatePublicSourcePage({
          sourceId,
          payload: {
            options,
            release_id: sourceReleaseId,
          },
        }).unwrap();
        setPublishButton({ text: "Done", color: "green" });
      } catch {
        setPublishButton({ text: "Error", color: "red" });
      }
      setTimeout(() => {
        setPublishButton({ text: "Publish", color: "" });
      }, 2000);
    }
  };

  return (
    <DialogContent sx={{ pb: 1 }}>
      <Box sx={{ mt: 2, mb: 2 }}>
        You are about to change the public access settings for this source page.
        The data you selected will be available to everyone on the internet. Are
        you sure you want to do this ?
      </Box>
      <Box sx={{ display: "flex", justifyContent: "center", my: 3 }}>
        <Tooltip
          title={
            manageSourcesAccess
              ? ""
              : "You do not have permission to publish this source"
          }
        >
          <div>
            <Button
              variant="contained"
              onClick={publish}
              sx={{ bgcolor: publishButton.color, color: "white" }}
              disabled={
                !manageSourcesAccess || publishButton.text !== "Publish"
              }
            >
              {publishButton.text === "loading" ? (
                <CircularProgress size={24} />
              ) : (
                publishButton.text
              )}
            </Button>
          </div>
        </Tooltip>
      </Box>
      <div>
        <Button
          sx={expandButtonSx}
          size="small"
          variant="text"
          onClick={() => setSourcePublishReleaseOpen(!sourcePublishReleaseOpen)}
        >
          Release {manageSourcesAccess ? "(optional)" : "list"}
          {sourcePublishReleaseOpen ? <ExpandLess /> : <ExpandMore />}
        </Button>
        {sourcePublishReleaseOpen && (
          <SourcePublishRelease
            sourceReleaseId={sourceReleaseId}
            setSourceReleaseId={setSourceReleaseId}
            setOptions={setOptions}
          />
        )}
      </div>
      {displayOptions && (
        <div>
          <Button
            sx={expandButtonSx}
            size="small"
            variant="text"
            onClick={() =>
              setSourcePublishOptionsOpen(!sourcePublishOptionsOpen)
            }
          >
            Options
            {sourcePublishOptionsOpen ? <ExpandLess /> : <ExpandMore />}
          </Button>
          {sourcePublishOptionsOpen && (
            <SourcePublishOptions
              options={options}
              setOptions={setOptions}
              isElements={isElements}
            />
          )}
        </div>
      )}
      <div>
        <Button
          sx={expandButtonSx}
          size="small"
          variant="text"
          onClick={() => setSourcePublishHistoryOpen(!sourcePublishHistoryOpen)}
        >
          Version history
          {sourcePublishHistoryOpen ? <ExpandLess /> : <ExpandMore />}
        </Button>
        {sourcePublishHistoryOpen && (
          <SourcePublishHistory sourceId={sourceId} />
        )}
      </div>
    </DialogContent>
  );
};

export default SourcePublish;
