import { useState } from "react";

import Typography from "@mui/material/Typography";
import UnfoldLessIcon from "@mui/icons-material/UnfoldLess";
import UnfoldMoreIcon from "@mui/icons-material/UnfoldMore";

import Button from "../../Button";
import Paper from "../../Paper";
import PreferencesPanel from "./PreferencesPanel";
import UIPreferences from "./UIPreferences";
import NotificationPreferences from "./NotificationPreferences";
import SlackPreferences from "./SlackPreferences";
import OpenAIPreferences from "./OpenAIPreferences";
import ObservabilityPreferences from "./ObservabilityPreferences";
import FollowupRequestPreferences from "./FollowupRequestPreferences";
import SetAutomaticallyVisiblePhotometry from "./SetAutomaticallyVisiblePhotometry";
import PhotometryButtonsForm from "./PhotometryButtonsForm";
import SpectroscopyButtonsForm from "./SpectroscopyButtonsForm";
import ClassificationsShortcutForm from "./ClassificationsShortcutForm";
import QuickSaveSourcePreferences from "./QuickSaveSourcePreferences";
import Box from "@mui/material/Box";

const PREFERENCE_PANELS = [
  {
    title: "Notifications",
    testId: "tour-profile-notifications",
    sections: [{ content: <NotificationPreferences /> }],
  },
  {
    title: "Integrations",
    sections: [
      {
        title: "Slack",
        popupText:
          "You'll need to ask your site administrator to give you a unique URL that posts to your Slack channel. Activating the Slack integration will allow you to get notifications on Slack, depending on your specific notification preferences.",
        content: <SlackPreferences />,
      },
      {
        title: "OpenAI summarization",
        popupText:
          "With an OpenAI account, you can use your API KEY to generate summaries of sources. This is a paid service, and while it does not cost that much per source (<$0.01) it can add up. So we ask you to use your own OpenAI account for this service. You can get your key here: https://platform.openai.com/account/api-keys",
        content: <OpenAIPreferences />,
      },
    ],
  },
  {
    title: "Interface",
    testId: "tour-profile-appearance",
    sections: [
      { content: <UIPreferences /> },
      {
        title: "Observability",
        popupText:
          "The telescopes to display observability plots for on sources' observability pages. You can see 16 telescopes at a time, and change page to see more.",
        content: <ObservabilityPreferences />,
      },
    ],
  },
  {
    title: "Sources",
    sections: [
      {
        title: "Classifications shortcut",
        popupText:
          "Select a group of preexisting classifications, give them a common name, and a shortcut button will appear on the scanning page for selecting those classifications.",
        content: <ClassificationsShortcutForm />,
      },
      {
        title: "Quick save",
        popupText:
          "Select the groups you would like to be able to quick save sources to. If any groups are selected, a quick save button will appear on the source page.",
        content: <QuickSaveSourcePreferences />,
      },
      {
        title: "Followup allocation",
        popupText: "The allocation to display first for followup requests",
        content: <FollowupRequestPreferences />,
      },
    ],
  },
  {
    title: "Plotting",
    sections: [
      {
        title: "Automatically visible photometry",
        popupText:
          "Select filters and origins which you would like to automatically be visible on the photometry plot. All other photometry points will be hidden, unless the plot does not contain your selected filters/origins.",
        content: <SetAutomaticallyVisiblePhotometry />,
      },
      {
        title: "Photometry buttons",
        popupText:
          "Select a group of filters and origins, give them a common name, and a button will appear on photometry plots for showing those filters/origins on the plot. The button will not hide the points already visible on the plot, it will only add the selected filters/origins to the visible points.",
        content: <PhotometryButtonsForm />,
      },
      {
        title: "Spectroscopy extra wavelengths",
        popupText:
          "Select a group of wavelengths, give them a common name and color, and a button will appear on spectroscopy plots for showing those spectral lines on the plot.",
        content: <SpectroscopyButtonsForm />,
      },
    ],
  },
];

const UserPreferences = () => {
  const [openPanels, setOpenPanels] = useState<string[]>([]);
  const allOpen = openPanels.length === PREFERENCE_PANELS.length;

  const togglePanel = (title: string) =>
    setOpenPanels((open) =>
      open.includes(title)
        ? open.filter((panel) => panel !== title)
        : [...open, title],
    );

  return (
    <Paper>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          mb: 2,
        }}
      >
        <Typography variant="h6">Preferences</Typography>
        <Button
          size="small"
          endIcon={allOpen ? <UnfoldLessIcon /> : <UnfoldMoreIcon />}
          onClick={() =>
            setOpenPanels(allOpen ? [] : PREFERENCE_PANELS.map((p) => p.title))
          }
        >
          {allOpen ? "Collapse all" : "Expand all"}
        </Button>
      </Box>
      {PREFERENCE_PANELS.map(({ title, testId, sections }) => (
        <PreferencesPanel
          key={title}
          title={title}
          testId={testId}
          sections={sections}
          expanded={openPanels.includes(title)}
          onToggle={() => togglePanel(title)}
        />
      ))}
    </Paper>
  );
};

export default UserPreferences;
