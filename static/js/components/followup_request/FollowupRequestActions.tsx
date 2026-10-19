import { useState } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import {
  useDeleteFollowupRequestMutation,
  useEditFollowupRequestMutation,
  useLazyGetPhotometryRequestQuery,
} from "../../ducks/source";
import Button from "../Button";

const ActionButton = ({
  loading = false,
  onClick,
  testId,
  children,
}: {
  loading?: boolean;
  onClick: () => void;
  testId?: string;
  children: string;
}) =>
  loading ? (
    <CircularProgress size={24} />
  ) : (
    <Button primary size="small" onClick={onClick} data-testid={testId}>
      {children}
    </Button>
  );

interface FollowupRequestActionsProps {
  request: any;
  methodsImplemented: { get?: boolean; delete?: boolean; submit?: boolean };
  editable: boolean;
  refresh: boolean;
  onEdit: (id: number) => void;
}

const FollowupRequestActions = ({
  request,
  methodsImplemented,
  editable,
  refresh,
  onEdit,
}: FollowupRequestActionsProps) => {
  const dispatch = useAppDispatch();
  const [deleteFollowupRequest] = useDeleteFollowupRequestMutation();
  const [editFollowupRequest] = useEditFollowupRequestMutation();
  const [getPhotometryRequest] = useLazyGetPhotometryRequestQuery();
  const [loading, setLoading] = useState<string | null>(null);
  const [hasRetrieved, setHasRetrieved] = useState(false);
  const params = refresh ? { refreshRequests: true } : {};
  const { id, status } = request;
  const isDeleted = status === "deleted";

  const run = async (action: string, callback: () => Promise<unknown>) => {
    setLoading(action);
    await callback();
    setLoading(null);
  };

  const retrieve = async () => {
    const { data, error }: any = await getPhotometryRequest({ id, params });
    if (error) return;
    dispatch(
      data?.request_status?.includes("rejected")
        ? showNotification("Request has been rejected.", "warning")
        : showNotification(
            "Request successfully submitted, please wait for it to be processed.",
            "info",
          ),
    );
    setHasRetrieved(true);
  };

  const canRetrieve =
    methodsImplemented.get &&
    !hasRetrieved &&
    status !== "Photometry committed to database" &&
    (status.startsWith("pending") || status.startsWith("submitted"));

  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, py: 0.5 }}>
      {methodsImplemented.delete && !isDeleted && (
        <ActionButton
          loading={loading === "delete"}
          onClick={() =>
            run("delete", () => deleteFollowupRequest({ id, params }))
          }
          testId={`deleteRequest_${id}`}
        >
          Delete
        </ActionButton>
      )}
      {canRetrieve && (
        <ActionButton
          loading={loading === "retrieve"}
          onClick={() => run("retrieve", retrieve)}
        >
          Retrieve
        </ActionButton>
      )}
      {methodsImplemented.submit && status.includes("failed to submit") && (
        <ActionButton
          loading={loading === "submit"}
          onClick={() =>
            run("submit", () =>
              editFollowupRequest({
                params: {
                  allocation_id: request.allocation.id,
                  obj_id: request.obj_id,
                  payload: request.payload,
                  ...params,
                },
                requestID: id,
              }),
            )
          }
        >
          Submit
        </ActionButton>
      )}
      {editable && !isDeleted && (
        <ActionButton onClick={() => onEdit(id)} testId={`editRequest_${id}`}>
          Edit
        </ActionButton>
      )}
    </Box>
  );
};

export default FollowupRequestActions;
