# Comment URL migration:

In a recent release we have changed the way
comments and annotations are accessed via the API.
This better accommodates comments and annotations
on different underlying data (e.g., spectra),
and makes it harder to accidentally get the wrong comment,
as the underlying object ID (source or spectrum)
must match the object that the comment/annotation
is associated with.

In the past, a comment was accessed via the endpoint
`api/comment/<commentID>`

In the new framework, a comment on a source must be accessed via
the source path:
`api/sources/<sourceID>/comments/<commentID>`

This also applies to comments on spectra:
`api/spectra/<spectrumID>/comments/<commentID>`

For annotations, use:
`api/sources/<sourceID>/annotations/<annotationID>`

In all cases, when posting a new comment/annotation,
do not supply a commentID or annotationID at the end of the path, e.g.,
POST to `api/sources/<sourceID>/comments`.

Any existing scripts that use the comment or annotation
API must be changed accordingly.
