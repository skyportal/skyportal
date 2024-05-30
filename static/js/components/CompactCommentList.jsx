import React from "react";
import ReactMarkdown from "react-markdown";
import { useSelector } from "react-redux";

import PropTypes from "prop-types";

import Tooltip from "@mui/material/Tooltip";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";

import UserAvatar from "./user/UserAvatar";
import DeleteComment from "./DeleteComment";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const CompactCommentList = ({
  associatedResourceType = "object",
  objID = null,
  gcnEventID = null,
  earthquakeID = null,
  styles = {},
  id = null,
  author = {},
  created_at = null,
  text = null,
  spectrum_id = null,
  hoverID = null,
  shiftID = null,
}) => {
  const spectra = useSelector((state) => state.spectra);

  const renderCommentText = () => {
    if (
      spectrum_id &&
      objID in spectra &&
      associatedResourceType === "object"
    ) {
      const spectrum = spectra[objID].find((spec) => spec.id === spectrum_id);
      const dayFraction =
        (parseFloat(spectrum.observed_at.substring(11, 13)) / 24) * 10;
      return `**Spectrum ${spectrum.observed_at.substring(
        2,
        10,
      )}.${dayFraction.toFixed(0)}** ${text}`;
    }

    return text;
  };

  const emojiSupport = (textComment) =>
    textComment.value.replace(/:\w+:/gi, (name) =>
      emoji.getUnicode(name) ? emoji.getUnicode(name) : name,
    );

  const commentMessageStyle =
    associatedResourceType === "shift"
      ? styles.compactCommentMessageShift
      : styles.compactCommentMessage;

  return (
    <div className={styles.compactContainer}>
      <div className={styles.commentUserAvatar}>
        <UserAvatar
          size={24}
          firstName={author.first_name}
          lastName={author.last_name}
          username={author.username}
          gravatarUrl={author.gravatar_url}
          isBot={author?.is_bot || false}
        />
      </div>
      <div
        className={styles.compactWrap}
        name={`commentDiv${(spectrum_id ? "Spectrum" : "Source") + id}`}
      >
        <ReactMarkdown
          className={commentMessageStyle}
          components={{ text: emojiSupport }}
        >
          {renderCommentText()}
        </ReactMarkdown>
        <div className={styles.compactButtons}>
          <Tooltip
            title={dayjs().to(dayjs.utc(`${created_at}Z`))}
            placement="left"
          >
            <InfoOutlinedIcon fontSize="small" />
          </Tooltip>
          <div className={styles.spacer}>
            <DeleteComment
              associatedResourceType={associatedResourceType}
              objID={objID}
              gcnEventID={gcnEventID}
              earthquakeID={earthquakeID}
              spectrum_id={spectrum_id}
              shiftID={shiftID}
              hoverID={hoverID}
              id={id}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

CompactCommentList.propTypes = {
  objID: PropTypes.string,
  gcnEventID: PropTypes.number,
  earthquakeID: PropTypes.number,
  associatedResourceType: PropTypes.string,
  styles: PropTypes.shape({}),
  id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  author: PropTypes.shape({}),
  created_at: PropTypes.string,
  text: PropTypes.string,
  spectrum_id: PropTypes.string,
  hoverID: PropTypes.number,
  shiftID: PropTypes.number,
};

CompactCommentList.defaultProps = {
  objID: null,
  gcnEventID: null,
  earthquakeID: null,
  associatedResourceType: "object",
  styles: {},
  id: null,
  author: {},
  created_at: null,
  text: null,
  spectrum_id: null,
  hoverID: null,
  shiftID: null,
};

export default CompactCommentList;
