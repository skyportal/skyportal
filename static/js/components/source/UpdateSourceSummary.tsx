import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { useUpdateSourceMutation } from "../../ducks/source";
import UpdateSummary from "../summary/UpdateSummary";

interface UpdateSourceSummaryProps {
  source: {
    id?: string;
    summary?: string | null;
    summary_history?: any[];
  };
  showAISummaries?: boolean;
  chip?: boolean;
}

const UpdateSourceSummary = ({
  source,
  showAISummaries = true,
  chip = false,
}: UpdateSourceSummaryProps) => {
  const dispatch = useAppDispatch();
  const [updateSource] = useUpdateSourceMutation();

  return (
    <UpdateSummary
      summary={source.summary}
      summaryHistory={source.summary_history}
      showAISummaries={showAISummaries}
      chip={chip}
      onSave={async (summary) => {
        await updateSource({ id: source.id!, payload: { summary } }).unwrap();
        dispatch(showNotification("Source summary successfully updated."));
      }}
    />
  );
};

export default UpdateSourceSummary;
