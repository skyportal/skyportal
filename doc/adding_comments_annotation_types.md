## Adding a new type of Comment or Annotation

`Comment`s and `Annotation`s are made by default on `Obj`s.
Some of the other data models can also be commented on or annotated.
An example is `Spectrum` that can be commented on and annotated
using `CommentOnSpectrum` and `AnnotationOnSpectrum`.

Here is a list of parts of the code that need to be modified
to allow comments or annotations on new types of data.
To make a new `Comment` type:
- Inherit from `CommentMixin` (as well as from `Base`).
- Add the name of the table to the `backref_name` function on `CommentMixin`.
- Add any additional columns, like a reference to a model the comment is on.
- Add the comment as a relationship with `back_populates` (etc.) on the model you are commenting on.
  (e.g., for `CommentOnSpectrum` you need to add `comments` to `models/spectrum.py`)
- Add a `join` to `models/group_joins.py` so comments will have groups associated with them.
- Add a `join` to `models/user_token.py` so comments will have a user associated with them.
- Update the API endpoints for comments, and the reducers to listen for changes in the comments.
- Update the `app_server.py` paths to accept the new type of comment upon API calls.

The list regards new `Comment` types on new data models,
but an equivalent list exists for new `Annotation` types.
As a detailed example, look for the `CommentOnSpectrum`
found in the abovementioned files.
