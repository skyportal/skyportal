import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetRecentSourcesQuery } from "../../ducks/recentSources";
import { useActiveTeam } from "../../ducks/teams";
import WidgetCard, { WidgetEmpty } from "./WidgetCard";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import { SourceListSkeleton, SourceRow } from "./SourceList";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs: any = {
  maxNumSources: "25",
  groupIds: [],
  includeSitewideSources: false,
  displayTNS: true,
};

const RecentSources = () => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const { activeTeam } = useActiveTeam();
  const { data: recentSources, isLoading } = useGetRecentSourcesQuery(
    activeTeam ? { teamID: activeTeam.id } : undefined,
  );
  const prefs = {
    ...defaultPrefs,
    ...((profile?.preferences?.["recentSources"] as any) ?? {}),
  };
  const sources = recentSources ?? [];

  return (
    <WidgetCard
      title="Recently saved"
      teamScoped
      actions={
        <WidgetPrefsDialog
          initialValues={prefs}
          stateBranchName="recentSources"
          title="Recently saved sources"
          onSubmit={updateUserPreferences}
        />
      }
    >
      {isLoading ? (
        <SourceListSkeleton />
      ) : sources.length === 0 ? (
        <WidgetEmpty>No recent sources.</WidgetEmpty>
      ) : (
        sources.map((source: any, idx: number) => (
          <SourceRow
            key={`recentSources_${source.obj_id}_${idx}`}
            source={source}
            testId={`recentSourceItem_${source.obj_id}_${source.created_at}`}
            meta={dayjs().to(dayjs.utc(`${source.created_at}Z`))}
            displayTNS={prefs.displayTNS !== false}
            showGroups
          />
        ))
      )}
    </WidgetCard>
  );
};

export default RecentSources;
