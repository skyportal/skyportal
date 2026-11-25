import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetTopSourcesQuery } from "../../ducks/topSources";
import { useActiveTeam } from "../../ducks/teams";
import WidgetCard, { WidgetEmpty } from "./WidgetCard";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import TimespanSelect from "./TimespanSelect";
import { SourceListSkeleton, SourceRow } from "./SourceList";

const defaultPrefs = {
  maxNumSources: "10",
  sinceDaysAgo: "7",
  displayTNS: true,
};

const TopSources = () => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const { activeTeam } = useActiveTeam();
  const { data: sourceViews, isLoading } = useGetTopSourcesQuery(
    activeTeam ? { teamID: activeTeam.id } : undefined,
  );
  const prefs = {
    ...defaultPrefs,
    ...((profile?.preferences as any)?.topSources ?? {}),
  };
  const sources = sourceViews ?? [];

  return (
    <WidgetCard
      title="Top sources"
      teamScoped
      actions={
        <>
          <TimespanSelect
            value={prefs.sinceDaysAgo}
            onChange={(sinceDaysAgo) =>
              updateUserPreferences({ topSources: { ...prefs, sinceDaysAgo } })
            }
            testIdPrefix="topSources"
          />
          <WidgetPrefsDialog
            initialValues={{
              maxNumSources: prefs.maxNumSources,
              displayTNS: prefs.displayTNS,
            }}
            stateBranchName="topSources"
            title="Top sources"
            onSubmit={updateUserPreferences}
          />
        </>
      }
    >
      {isLoading ? (
        <SourceListSkeleton />
      ) : sources.length === 0 ? (
        <WidgetEmpty>No source views in this period.</WidgetEmpty>
      ) : (
        sources.map((source: any) => (
          <SourceRow
            key={`topSources_${source.obj_id}`}
            source={source}
            testId={`topSourceItem_${source.obj_id}_${source.created_at}`}
            meta={`${source.views} view${source.views !== 1 ? "s" : ""}`}
            displayTNS={prefs.displayTNS !== false}
          />
        ))
      )}
    </WidgetCard>
  );
};

export default TopSources;
