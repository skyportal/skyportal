import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from skyportal.models import DBSession, PhotometricSeries

env, cfg = load_env()

init_db(**cfg["database"])

if __name__ == "__main__":
    page, total_processed = 0, 0
    while True:
        with DBSession() as session:
            try:
                ids: list[int] = session.scalars(
                    sa.select(PhotometricSeries.id)
                    .order_by(PhotometricSeries.id)
                    .distinct()
                    .offset(page * 1000)
                    .limit(1000)
                ).all()
            except Exception as e:
                print(f"Error fetching objects: {e}")
                break
            if not ids:
                break
            for id in ids:
                try:
                    phot_series = session.scalar(
                        sa.select(PhotometricSeries).where(PhotometricSeries.id == id)
                    )

                    # if no photometric series exists, skip
                    if not phot_series:
                        print(
                            f"Warning - No photometric series found for id {id}, skipping."
                        )
                        continue

                    # lazily-load the data needed to calculate stats
                    phot_series.load_data()
                    phot_series.calc_flux_mag()
                    phot_series.calc_stats()

                    session.commit()
                except Exception as e:
                    print(f"Error processing photometric series {id}: {e}")
                    session.rollback()
                    continue

        page += 1
        total_processed += len(ids)
        print(f"Processed page {page} (total={total_processed})")

    print(f"Total processed: {total_processed}")
