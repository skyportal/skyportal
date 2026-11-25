import { useGetPaperCornerQuery } from "../../ducks/paperCorner";
import PaperList from "../source/PaperList";
import WidgetCard, { WidgetEmpty } from "./WidgetCard";
import WidgetLoading from "./WidgetLoading";

const PaperCorner = () => {
  const { data, isLoading, isError } = useGetPaperCornerQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  let message = "No matching papers.";
  if (isError) message = "Paper Corner is temporarily unavailable.";
  else if (!data?.enabled) message = "Paper Corner is disabled.";
  else if (data.pending) message = "Waiting for the first ADS refresh.";

  return (
    <WidgetCard title="Paper Corner">
      {isLoading ? (
        <WidgetLoading />
      ) : data?.papers.length ? (
        <PaperList papers={data.papers} linkSources />
      ) : (
        <WidgetEmpty>
          <span role="status">{message}</span>
        </WidgetEmpty>
      )}
    </WidgetCard>
  );
};

export default PaperCorner;
