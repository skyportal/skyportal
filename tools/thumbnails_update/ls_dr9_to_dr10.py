import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from skyportal.models import DBSession, Obj, Thumbnail

env, cfg = load_env()

init_db(**cfg["database"])

if __name__ == "__main__":
    page, total_processed = 0, 0
    while True:
        with DBSession() as session:
            try:
                obj_ids: list[str] = session.scalars(
                    sa.select(Obj.id)
                    .order_by(Obj.id)
                    .distinct()
                    .offset(page * 1000)
                    .limit(1000)
                ).all()
            except Exception as e:
                print(f"Error fetching objects: {e}")
                break
            if not obj_ids:
                break
            for obj_id in obj_ids:
                try:
                    thumbnails: list[Thumbnail] = session.scalars(
                        sa.select(Thumbnail).where(
                            Thumbnail.obj_id == obj_id, Thumbnail.type == "ls"
                        )
                    ).all()

                    # if no thumbnail exists, create one
                    if not thumbnails:
                        obj: Obj = session.scalar(
                            sa.select(Obj).where(Obj.id == obj_id)
                        )
                        session.add(
                            Thumbnail(
                                obj=obj, public_url=obj.legacysurvey_dr10_url, type="ls"
                            )
                        )
                        session.commit()
                        continue

                    # delete duplicate thumbnails if any
                    if len(thumbnails) > 1:
                        for thumbnail in thumbnails[1:]:
                            session.delete(thumbnail)
                        session.commit()

                    # update the existing thumbnail, if necessary
                    public_url: str = thumbnails[0].public_url
                    if public_url is None:
                        print(
                            f"Warning: LS thumbnail for obj_id {obj_id} is None, which is unexpected."
                        )
                        continue
                    if "layer=ls-dr10" and "bands=griz" in public_url:
                        continue
                    public_url = public_url.replace(
                        "layer=ls-dr9", "layer=ls-dr10"
                    ).replace("bands=grz", "bands=griz")
                    thumbnails[0].public_url = public_url
                    session.commit()
                except Exception as e:
                    print(f"Error processing obj_id {obj_id}: {e}")
                    session.rollback()
                    continue

        page += 1
        total_processed += len(obj_ids)
        print(f"Processed page {page} (total={total_processed})")

    print(f"Total processed: {total_processed}")
