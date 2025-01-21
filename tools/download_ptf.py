"""Scrape data from PTF marshal website and saves to disk/local `ptf` database."""

import html
import os.path
import re
from datetime import datetime

import requests
import sqlalchemy as sa
from requests.auth import HTTPBasicAuth
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

pBase = automap_base()
pengine = create_engine("postgresql://skyportal:@localhost:5432/ptf")


class pComment(pBase):
    __tablename__ = "comments"
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #    username = sa.Column(sa.String, nullable=False, index=True)
    text = sa.Column(sa.String, nullable=False)
    obj_id = sa.Column(
        sa.ForeignKey("sources.name", ondelete="CASCADE"), nullable=False, index=True
    )
    date_added = sa.Column(sa.DateTime, nullable=False)


pBase.prepare(pengine, reflect=True)
pBase.metadata.bind = pengine
pBase.metadata.create_all()

pUser = pBase.classes.users
pSource = pBase.classes.sources

psession = Session(pengine)


def download_source_info(obj_id, auth, out_dir):
    """Download thumbnails, comments, spectra for source from PTF Marshal."""
    source_page = requests.get(
        f"http://ptf.caltech.edu/cgi-bin/ptf/transient/view_source.cgi?name={obj_id}",
        auth=auth,
    )
    lines = html.unescape(source_page.text).split("\n")
    comment_inds = [i for i, l in enumerate(lines) if "[info]" in l]
    for i in comment_inds:
        info = lines[i].split()
        comment_date = datetime.strptime(" ".join(info[:3]), "%Y %b %d")
        comment_username = info[3]
        comment_user = (
            psession.query(pUser).filter(pUser.username == comment_username).first()
        )
        if comment_user is None:
            continue
        comment_text = lines[i + 1].strip()
        comment_text = re.sub(
            r" *\[<a.*<\/a>]", "", comment_text
        )  # remove attachment link
        c = pComment(
            user_id=comment_user.id,
            text=comment_text,
            date_added=comment_date,
            obj_id=obj_id,
        )
        psession.add(c)
        psession.commit()

    spectra = requests.get(
        f"http://ptf.caltech.edu/cgi-bin/ptf/transient/batch_spec.cgi?name={obj_id}",
        auth=auth,
    )
    if not spectra.content.startswith(b"No spectrum is found"):
        with open(os.path.join(out_dir, "spectra", f"{obj_id}.tar.gz"), "wb") as f:
            f.write(spectra.content)

    for filename in [f"{obj_id}_new.png", f"{obj_id}_ref.png", f"{obj_id}_sub.png"]:
        cutout = requests.get(
            f"http://ptf.caltech.edu/marshals/transient/ptf/thumbs/{filename}",
            auth=auth,
        )
        if not cutout.ok:
            print(f"No cutouts found for {obj_id}")
            break
        with open(os.path.join(out_dir, "cutouts", filename), "wb") as f:
            f.write(cutout.content)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("user")
    parser.add_argument("password")
    parser.add_argument("out_dir")
    args = parser.parse_args()
    auth = HTTPBasicAuth(args.user, args.password)
    for subdir in ["spectra", "cutouts"]:
        try:
            os.mkdir(os.path.join(args.out_dir, subdir))
        except FileExistsError:
            pass

#    from tqdm import tqdm
#    for source in tqdm(list(psession.query(pSource))):
#        try:
#            download_source_info(source.name, auth, args.out_dir)
#        except Exception as e:
#            print(f'Failed to download f{source.id}')
#            print(e)
