import { useEffect, useState } from "react";
import CancelScheduleSendIcon from "@mui/icons-material/CancelScheduleSend";
import CancelScheduleSendOutlinedIcon from "@mui/icons-material/CancelScheduleSendOutlined";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";

import { useUpdateSourceMutation } from "../../ducks/source";

interface WithholdFromTNSProps {
  source: {
    id: string;
    withhold_from_tns?: boolean;
    withhold_from_tns_set_at?: string | null;
    withhold_from_tns_set_by?: { username?: string } | null;
  };
  readOnly?: boolean;
}

const WithholdFromTNS = ({
  source,
  readOnly = false,
}: WithholdFromTNSProps) => {
  const [updateSource] = useUpdateSourceMutation();
  const [withheld, setWithheld] = useState(Boolean(source.withhold_from_tns));

  useEffect(() => {
    setWithheld(Boolean(source.withhold_from_tns));
  }, [source.withhold_from_tns]);

  const toggle = async () => {
    const next = !withheld;
    setWithheld(next);
    const result = await updateSource({
      id: source.id,
      payload: { withhold_from_tns: next },
    });
    if ("error" in result) setWithheld(!next);
  };

  const setBy =
    withheld && source.withhold_from_tns && source.withhold_from_tns_set_at
      ? ` (blocked by ${
          source.withhold_from_tns_set_by?.username ?? "a deleted user"
        } on ${source.withhold_from_tns_set_at.slice(0, 10)})`
      : "";

  return (
    <Tooltip
      title={
        withheld
          ? `Click to allow it to be sent to TNS again${setBy}`
          : "Click to stop it from being sent to TNS, automatically or manually"
      }
    >
      <span>
        <IconButton
          size="small"
          data-testid="withhold-from-tns-button"
          aria-pressed={withheld}
          disabled={readOnly}
          onClick={toggle}
          sx={{
            p: 0,
            ml: 0.5,
            color: withheld ? "error.main" : "text.disabled",
            "&:hover": { color: "error.main" },
            "& .MuiSvgIcon-root": { fontSize: 17 },
          }}
        >
          {withheld ? (
            <CancelScheduleSendIcon />
          ) : (
            <CancelScheduleSendOutlinedIcon />
          )}
        </IconButton>
      </span>
    </Tooltip>
  );
};

export default WithholdFromTNS;
