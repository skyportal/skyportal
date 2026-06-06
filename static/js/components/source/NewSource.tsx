import { useGetGroupsQuery } from "../../ducks/groups";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { useAppDispatch } from "../../types/hooks";
import GroupShareSelect from "../group/GroupShareSelect";
import {
  useLazyCheckSourceQuery,
  useSaveSourceMutation,
} from "../../ducks/source";
import { dms_to_dec, hours_to_ra } from "../../units";

dayjs.extend(utc);

interface NewSourceProps {
  classes: {
    widgetPaperDiv: string;
  };
  onClose?: () => void;
}

const NewSource = ({ classes, onClose = () => ({}) }: NewSourceProps) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [checkSource] = useLazyCheckSourceQuery();
  const [saveSource] = useSaveSourceMutation();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);
  const [selectedFormData, setSelectedFormData] = useState<any>({
    id: "",
    ra: "",
    dec: "",
  });

  const handleSubmit = async ({ formData }: { formData: any }) => {
    const dataToSend: any = {
      ...formData,
    };
    if (dataToSend?.ra?.includes(":")) {
      dataToSend.ra = hours_to_ra(dataToSend?.ra);
    } else {
      dataToSend.ra = parseFloat(dataToSend?.ra);
    }
    if (dataToSend?.dec?.includes(":")) {
      dataToSend.dec = dms_to_dec(dataToSend?.dec);
    } else {
      dataToSend.dec = parseFloat(dataToSend?.dec);
    }
    if (
      dataToSend?.id === "" ||
      dataToSend?.id === null ||
      dataToSend?.id === undefined ||
      !dataToSend?.id
    ) {
      dispatch(showNotification("Please enter a source ID.", "error"));
    } else {
      try {
        const data: any = await checkSource({
          id: dataToSend?.id,
          params: dataToSend,
        }).unwrap();
        if (data?.source_exists === true) {
          dispatch(showNotification(data.message, "error"));
          return;
        }

        if (selectedGroupIds.length > 0) {
          dataToSend.group_ids = selectedGroupIds;
        }
        await saveSource(dataToSend).unwrap();
        onClose();
        dispatch(showNotification("Source saved"));
        navigate(`/source/${dataToSend.id}`);
      } catch {
        // error notification handled by the baseQuery
      }
    }
  };

  function validate(formData: any, errors: any) {
    if (selectedGroupIds?.length === 0 && formData?.id !== "") {
      errors.__errors.push("Select at least one group.");
    }
    if ((formData?.ra !== "" || formData?.dec !== "") && formData?.id === "") {
      errors.id.addError("Please enter a source ID.");
    }
    if ((formData?.id || "").indexOf(" ") >= 0) {
      errors.id.addError("IDs are not allowed to have spaces, please fix.");
    }
    if ((formData?.ra || "").includes(":")) {
      formData.ra = hours_to_ra(formData.ra);
    } else {
      formData.ra = parseFloat(formData.ra);
    }
    if (formData?.ra < 0 || formData?.ra >= 360) {
      errors.ra.addError("0 <= RA < 360, please fix.");
    }
    if ((formData?.dec || "").includes(":")) {
      formData.dec = dms_to_dec(formData.dec);
    } else {
      formData.dec = parseFloat(formData.dec);
    }
    if (formData?.dec < -90 || formData?.dec > 90) {
      errors.ra.addError("-90 <= Declination <= 90, please fix.");
    }
    return errors;
  }

  const sourceFormSchema = {
    type: "object",
    properties: {
      id: {
        type: "string",
        title: "object ID",
      },
      ra: {
        type: "string",
        title: "Right Ascension [decimal deg. or HH:MM:SS]",
      },
      dec: {
        type: "string",
        title: "Declination [decimal deg. or DD:MM:SS]",
      },
    },
    required: ["id", "ra", "dec"],
  };

  return (
    <div className={classes.widgetPaperDiv}>
      <div>
        <Typography variant="h6" display="inline">
          Add a Source
        </Typography>
        <div>
          <GroupShareSelect
            groupList={groups}
            setGroupIDs={setSelectedGroupIds}
            groupIDs={selectedGroupIds}
          />
          <Form
            schema={sourceFormSchema as any}
            formData={selectedFormData}
            onChange={
              (({ formData }: { formData: any }) =>
                setSelectedFormData(formData)) as any
            }
            validator={validator}
            onSubmit={handleSubmit as any}
            customValidate={validate}
          />
        </div>
      </div>
    </div>
  );
};

export default NewSource;
