from astropy.time import Time
from skyportal_py_models.telescopes import (
    TelescopeGetQuery,
    TelescopePostBody,
    TelescopePostResponse,
    TelescopePutBody,
)
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions

from ...models import Allocation, AllocationUser, Instrument, Telescope
from ..base import BaseHandler


class TelescopeHandler(BaseHandler):
    @auth_or_token
    async def post(self, *, body: TelescopePostBody = None) -> TelescopePostResponse:
        """
        ---
        summary: Create a telescope
        description: Create telescopes
        tags:
          - telescopes
        """
        body = self.parse_body(TelescopePostBody)

        async with self.AsyncSession() as session:
            # check if the telescope has a fixed location
            if body.fixed_location:
                if body.lat is None or body.lon is None or body.elevation is None:
                    return self.error(
                        "Missing latitude, longitude, or elevation; required if the telescope is fixed"
                    )
                elif (
                    body.lat < -90
                    or body.lat > 90
                    or body.lon < -180
                    or body.lon > 180
                    or body.elevation < 0
                ):
                    return self.error(
                        "Latitude must be between -90 and 90, longitude between -180 and 180, and elevation must be positive"
                    )
            telescope = Telescope(**body.model_dump(exclude_unset=True))
            session.add(telescope)
            await session.commit()

            self.push_all(action="skyportal/REFRESH_TELESCOPES")
            self.push_notification("Telescope created successfully")
            return self.success(data={"id": telescope.id})

    @auth_or_token
    async def get(
        self, telescope_id: int | None = None, *, query: TelescopeGetQuery = None
    ):
        """
        ---
        single:
          summary: Get a telescope
          description: Retrieve a telescope
          tags:
            - telescopes
          responses:
            200:
              content:
                application/json:
                  schema: SingleTelescope
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get all telescopes
          description: Retrieve all telescopes
          tags:
            - telescopes
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfTelescopes
            400:
              content:
                application/json:
                  schema: Error
        """
        query = self.parse_query(TelescopeGetQuery)

        async with self.AsyncSession() as session:
            if telescope_id is not None:
                single_result = await session.scalars(
                    Telescope.select(session.user_or_token)
                    .options(
                        selectinload(Telescope.instruments).selectinload(
                            Instrument.allocations
                        )
                    )
                    .where(Telescope.id == int(telescope_id))
                )
                t = single_result.first()
                if t is None:
                    return self.error(
                        f"Could not load telescope with ID {telescope_id}"
                    )
                instruments = []
                allocations = []
                for instrument in t.instruments:
                    instruments.append(instrument.to_dict())
                    allocations.extend(
                        [allocation.to_dict() for allocation in instrument.allocations]
                    )
                data = {
                    **t.to_dict(),
                    "instruments": instruments,
                    "allocations": allocations,
                }
                return self.success(data=data)

            stmt = Telescope.select(session.user_or_token).options(
                selectinload(Telescope.instruments)
                .selectinload(Instrument.allocations)
                .selectinload(Allocation.allocation_users)
                .selectinload(AllocationUser.user)
            )
            if query.name is not None:
                stmt = stmt.where(Telescope.name == query.name)
            if query.latitudeMin is not None:
                stmt = stmt.where(Telescope.lat >= query.latitudeMin)
            if query.latitudeMax is not None:
                stmt = stmt.where(Telescope.lat <= query.latitudeMax)
            if query.longitudeMin is not None:
                stmt = stmt.where(Telescope.lon >= query.longitudeMin)
            if query.longitudeMax is not None:
                stmt = stmt.where(Telescope.lon <= query.longitudeMax)

            list_result = await session.scalars(stmt)
            data = list_result.all()
            telescopes = []
            for telescope in data:
                if telescope is None:
                    continue
                temp = telescope.to_dict()
                temp = {**temp, **telescope.current_time()}
                temp["morning"] = (
                    temp["morning"].iso if isinstance(temp["morning"], Time) else False
                )
                temp["evening"] = (
                    temp["evening"].iso if isinstance(temp["evening"], Time) else False
                )

                allocations = []
                for instrument in telescope.instruments:
                    for allocation in instrument.allocations:
                        allocation_data = allocation.to_dict()
                        allocation_data["allocation_users"] = [
                            user.user.to_dict() for user in allocation.allocation_users
                        ]
                        allocations.append(allocation_data)
                temp["allocations"] = allocations
                telescopes.append(temp)

            return self.success(data=telescopes)

    @permissions(["Manage telescopes"])
    async def put(self, telescope_id: int, *, body: TelescopePutBody = None):
        """
        ---
        summary: Update a telescope
        description: Update telescope
        tags:
          - telescopes
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        body = self.parse_body(TelescopePutBody)

        async with self.AsyncSession() as session:
            telescope = await session.scalar(
                Telescope.select(session.user_or_token, mode="update").where(
                    Telescope.id == int(telescope_id)
                )
            )
            if telescope is None:
                return self.error("Invalid telescope ID.")

            changed = []
            for key in body.model_fields_set:
                value = getattr(body, key)
                if getattr(telescope, key) != value:
                    setattr(telescope, key, value)
                    changed.append(key)

            if not changed:
                self.push_notification("Nothing to update")
                return self.success()

            await session.commit()

            if any(k in changed for k in ("lat", "lon", "elevation")):
                telescope.current_time(refresh=True)

            self.push_all(action="skyportal/REFRESH_TELESCOPES")
            self.push_notification("Telescope updated successfully")
            return self.success()

    @permissions(["Manage telescopes"])
    async def delete(self, telescope_id: int):
        """
        ---
        summary: Delete a telescope
        description: Delete a telescope
        tags:
          - telescopes
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        async with self.AsyncSession() as session:
            del_result = await session.scalars(
                Telescope.select(session.user_or_token, mode="delete").where(
                    Telescope.id == int(telescope_id)
                )
            )
            t = del_result.first()
            if t is None:
                return self.error("Invalid telescope ID.")
            await session.delete(t)
            await session.commit()
            self.push_all(action="skyportal/REFRESH_TELESCOPES")
            return self.success()
