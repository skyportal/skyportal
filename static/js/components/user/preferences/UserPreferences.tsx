import { useSearchParams } from "react-router-dom";

import Link from "@mui/material/Link";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import Paper from "../../Paper";
import { useGetProfileQuery } from "../../../ducks/profile";
import JoinableStreamsList from "../JoinableStreamsList";
import NewTokenForm from "../NewTokenForm";
import TokenList from "../TokenList";
import PreferencesPanel, { PreferencesSection } from "./PreferencesPanel";
import UIPreferences from "./UIPreferences";
import NotificationPreferences from "./NotificationPreferences";
import OpenAIPreferences from "./OpenAIPreferences";
import ObservabilityPreferences from "./ObservabilityPreferences";
import FollowupRequestPreferences from "./FollowupRequestPreferences";
import SetAutomaticallyVisiblePhotometry from "./SetAutomaticallyVisiblePhotometry";
import PhotometryButtonsForm from "./PhotometryButtonsForm";
import SpectroscopyButtonsForm from "./SpectroscopyButtonsForm";
import ClassificationsShortcutForm from "./ClassificationsShortcutForm";
import QuickSaveSourcePreferences from "./QuickSaveSourcePreferences";

interface ProfileTab {
  title: string;
  testId?: string;
  sections: PreferencesSection[];
}

const SETTINGS: ProfileTab[] = [
  {
    title: "Notifications",
    testId: "tour-profile-notifications",
    sections: [{ content: <NotificationPreferences /> }],
  },
  {
    title: "Interface",
    testId: "tour-profile-appearance",
    sections: [
      {
        title: "Display",
        content: <UIPreferences />,
      },
      {
        title: "Observability",
        text: "Telescopes on observability plots.",
        content: <ObservabilityPreferences />,
      },
    ],
  },
  {
    title: "Sources",
    sections: [
      {
        title: "Classification shortcuts",
        text: "Scanning page buttons that select several classifications.",
        content: <ClassificationsShortcutForm />,
      },
      {
        title: "Quick save",
        text: "Groups the quick save button saves to.",
        content: <QuickSaveSourcePreferences />,
      },
      {
        title: "Follow-up allocation",
        text: "Default allocation for follow-up requests.",
        content: <FollowupRequestPreferences />,
      },
      {
        title: "Personal OpenAI key",
        text: (
          <>
            Use your own OpenAI account for summaries.{" "}
            <Link
              href="https://platform.openai.com/account/api-keys"
              target="_blank"
              rel="noreferrer"
            >
              Get a key
            </Link>
          </>
        ),
        content: <OpenAIPreferences />,
      },
    ],
  },
  {
    title: "Plotting",
    sections: [
      {
        title: "Visible photometry",
        text: "Filters and origins shown by default on photometry plots.",
        content: <SetAutomaticallyVisiblePhotometry />,
      },
      {
        title: "Photometry buttons",
        text: "Photometry plot buttons that show a set of filters and origins.",
        content: <PhotometryButtonsForm />,
      },
      {
        title: "Spectral lines",
        text: "Spectroscopy plot buttons that draw a set of lines.",
        content: <SpectroscopyButtonsForm />,
      },
    ],
  },
];

const slug = (title: string) => title.toLowerCase().replace(/\s+/g, "-");

const UserPreferences = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: profile } = useGetProfileQuery();

  const tabs: ProfileTab[] = [
    ...SETTINGS,
    {
      title: "Streams",
      sections: [
        {
          title: "Public streams",
          content: <JoinableStreamsList />,
        },
      ],
    },
    {
      title: "API tokens",
      testId: "tour-profile-token",
      sections: [
        {
          title: "New token",
          text: "To use the API from scripts.",
          content: <NewTokenForm availableAcls={profile?.permissions} />,
        },
        { content: <TokenList tokens={(profile as any)?.tokens} /> },
      ],
    },
  ];
  const current =
    tabs.find((tab) => slug(tab.title) === searchParams.get("tab")) ?? tabs[0]!;

  return (
    <Paper>
      <Tabs
        value={slug(current.title)}
        onChange={(_, value) =>
          setSearchParams({ tab: value }, { replace: true })
        }
        variant="scrollable"
        sx={{ borderBottom: 1, borderColor: "divider", marginBottom: 2.5 }}
      >
        {tabs.map(({ title, testId }) => (
          <Tab
            key={title}
            value={slug(title)}
            label={<span data-testid={testId}>{title}</span>}
            data-testid={`${slug(title)}-panel`}
          />
        ))}
      </Tabs>
      <PreferencesPanel sections={current.sections} />
    </Paper>
  );
};

export default UserPreferences;
