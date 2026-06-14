import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token

from ....models import GalaxyCatalog, Instrument
from ...base import BaseHandler


class RoboticInstrumentsHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        apitype = self.get_query_argument("apiType", "api_classname")
        async with self.AsyncSession() as session:
            if apitype is not None:
                if apitype == "api_classname":
                    result = await session.scalars(
                        Instrument.select(session.user_or_token).where(
                            Instrument.api_classname.isnot(None)
                        )
                    )
                    instruments = result.all()
                    retval = {
                        i.id: i.api_class.frontend_render_info(i, session.user_or_token)
                        for i in instruments
                    }
                elif apitype == "api_classname_obsplan":
                    result = await session.scalars(
                        Instrument.select(session.user_or_token)
                        # custom_json_schema reads instrument.telescope
                        # (next_twilight_morning_nautical); eager-load it so it
                        # doesn't lazy-load (MissingGreenlet) under async.
                        .options(joinedload(Instrument.telescope))
                        .where(Instrument.api_classname_obsplan.isnot(None))
                    )
                    instruments = result.all()

                    # we retrieve the list of unique galaxy catalog names here
                    # and pass them to the frontend_render_info method
                    # to avoid having to run that query for each instrument
                    galaxy_result = await session.scalars(
                        sa.select(GalaxyCatalog.name).distinct()
                    )
                    galaxy_catalog_names = galaxy_result.all()
                    retval = {
                        i.id: i.api_class_obsplan.frontend_render_info(
                            i,
                            session.user_or_token,
                            galaxy_catalog_names=galaxy_catalog_names,
                        )
                        for i in instruments
                    }
                else:
                    return self.error(
                        f"apitype can only be api_classname or api_classname_obsplan, not {apitype}"
                    )
            return self.success(data=retval)
