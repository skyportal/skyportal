import * as API from "../API";
import store from "../store";

const ADD_GENERAL_COMMENT = "skyportal/ADD_GENERAL_COMMENT";

const DELETE_GENERAL_COMMENT = "skyportal/DELETE_GENERAL_COMMENT";

const GET_GENERAL_COMMENT_ATTACHMENT =
  "skyportal/GET_GENERAL_COMMENT_ATTACHMENT";
const GET_GENERAL_COMMENT_ATTACHMENT_OK =
  "skyportal/GET_GENERAL_COMMENT_ATTACHMENT_OK";

const GET_GENERAL_COMMENT_ATTACHMENT_PREVIEW =
  "skyportal/GET_GENERAL_COMMENT_ATTACHMENT_PREVIEW";
const GET_GENERAL_COMMENT_ATTACHMENT_PREVIEW_OK =
  "skyportal/GET_GENERAL_COMMENT_ATTACHMENT_PREVIEW_OK";

export function addGeneralComment(formData) {
  function fileReaderPromise(file) {
    return new Promise((resolve) => {
      const filereader = new FileReader();
      filereader.readAsDataURL(file);
      filereader.onloadend = () =>
        resolve({ body: filereader.result, name: file.name });
    });
  }
  if (formData.attachment) {
    return (dispatch) => {
      fileReaderPromise(formData.attachment).then((fileData) => {
        formData.attachment = fileData;

        dispatch(API.POST(`/api/comments`, ADD_GENERAL_COMMENT, formData));
      });
    };
  }

  return API.POST(`/api/comments`, ADD_GENERAL_COMMENT, formData);
}

export function deleteGeneralComment(commentID) {
  return API.DELETE(`/api/comments/${commentID}`, DELETE_GENERAL_COMMENT);
}

export function getGeneralCommentAttachment(commentID) {
  return API.GET(
    `/api/comments/${commentID}/attachment`,
    GET_GENERAL_COMMENT_ATTACHMENT
  );
}

export function getGeneralCommentAttachmentPreview(commentID) {
  return API.GET(
    `/api/comments/${commentID}`,
    GET_GENERAL_COMMENT_ATTACHMENT_PREVIEW
  );
}

const reducer = (state = { source: null, loadError: false }, action) => {
  switch (action.type) {
    case GET_GENERAL_COMMENT_ATTACHMENT_OK: {
      const { commentId, text, attachment, attachment_name } = action.data;
      return {
        ...state,
        commentAttachment: {
          commentId,
          text,
          attachment,
          attachment_name,
        },
      };
    }
    case GET_GENERAL_COMMENT_ATTACHMENT_PREVIEW_OK: {
      const { commentId, text, attachment, attachment_name } = action.data;
      return {
        ...state,
        commentAttachment: {
          commentId,
          text,
          attachment,
          attachment_name,
        },
      };
    }
    default:
      return state;
  }
};

store.injectReducer("GeneralComments", reducer);
