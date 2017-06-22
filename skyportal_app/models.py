import os
import pandas as pd

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import init_db, Base, DBSession, User
from cesium import featurize


class Annotation(Base):
    pass


class Photometry(Base):
    pass


class Source(Base)


#user_projects = sa.Table('user_projects', Base.metadata,
#                         sa.Column('user_id', sa.ForeignKey('users.id',
#                                                            ondelete='CASCADE'),
#                                   primary_key=True),
#                         sa.Column('project_id', sa.ForeignKey('projects.id',
#                                                               ondelete='CASCADE'),
#                                   primary_key=True))
#User.projects = relationship('Project', secondary=user_projects,
#                             back_populates='users', cascade='all')
#
#
#class Dataset(Base):
#    name = sa.Column(sa.String(), nullable=False)
#    meta_features = sa.Column(sa.ARRAY(sa.VARCHAR()), nullable=False,
#                              default=[], index=True)
#    project_id = sa.Column(sa.ForeignKey('projects.id', ondelete='CASCADE'),
#                           nullable=False, index=True)
#    project = relationship('Project', back_populates='datasets')
#    files = relationship('DatasetFile', backref='dataset', cascade='all')
#
#    def display_info(self):
#        info = self.to_dict()
#        info['files'] = [os.path.basename(f.name) for f in self.files]
#
#        return info
#
#
#class DatasetFile(Base):
#    dataset_id = sa.Column(sa.ForeignKey('datasets.id', ondelete='CASCADE'),
#                           nullable=False, index=True)
#    uri = sa.Column(sa.String(), nullable=False)
#    name = sa.Column(sa.String(), nullable=False, default=lambda context:
#                     context.current_parameters.get('uri'))
#
#
#class Project(Base):
#    name = sa.Column(sa.String(), nullable=False)
#    description = sa.Column(sa.String())
#    users = relationship('User', secondary=user_projects,
#                         back_populates='projects')
#    datasets = relationship('Dataset', back_populates='project',
#                            cascade='all')
#    featuresets = relationship('Featureset', back_populates='project',
#                               cascade='all')
#    models = relationship('Model', back_populates='project', cascade='all')
#    predictions = relationship('Prediction', back_populates='project',
#                               cascade='all')
#
#
#class Featureset(Base):
#    project_id = sa.Column(sa.ForeignKey('projects.id', ondelete='CASCADE'),
#                           nullable=False, index=True)
#    project = relationship('Project', back_populates='featuresets')
#    name = sa.Column(sa.String(), nullable=False)
#    features_list = sa.Column(sa.ARRAY(sa.VARCHAR()), nullable=False, index=True)
#    custom_features_script = sa.Column(sa.String())
#    file_uri = sa.Column(sa.String(), nullable=True, index=True)
#    task_id = sa.Column(sa.String())
#    finished = sa.Column(sa.DateTime)
#
#    project = relationship('Project')
#
#
#class Model(Base):
#    project_id = sa.Column(sa.ForeignKey('projects.id', ondelete='CASCADE'),
#                           nullable=False, index=True)
#    project = relationship('Project', back_populates='models')
#    featureset_id = sa.Column(sa.ForeignKey('featuresets.id',
#                                            ondelete='CASCADE'),
#                              nullable=False, index=True)
#    name = sa.Column(sa.String(), nullable=False)
#    params = sa.Column(sa.JSON, nullable=False, index=False)
#    type = sa.Column(sa.String(), nullable=False)
#    file_uri = sa.Column(sa.String(), nullable=True, index=True)
#    task_id = sa.Column(sa.String())
#    finished = sa.Column(sa.DateTime)
#    train_score = sa.Column(sa.Float)
#
#    featureset = relationship('Featureset')
#    project = relationship('Project')
#
#
#class Prediction(Base):
#    project_id = sa.Column(sa.ForeignKey('projects.id', ondelete='CASCADE'),
#                           nullable=False, index=True)
#    project = relationship('Project', back_populates='predictions')
#    dataset_id = sa.Column(sa.ForeignKey('datasets.id', ondelete='CASCADE'),
#                           nullable=False, index=True)
#    model_id = sa.Column(sa.ForeignKey('models.id', ondelete='CASCADE'),
#                         nullable=False, index=True)
#    file_uri = sa.Column(sa.String(), nullable=True, index=True)
#    task_id = sa.Column(sa.String())
#    finished = sa.Column(sa.DateTime)
#
#    dataset = relationship('Dataset')
#    model = relationship('Model')
#    project = relationship('Project')
#
#    def format_pred_data(fset, data):
#        fset.columns = fset.columns.droplevel('channel')
#
#        labels = pd.Series(data['labels'] if len(data.get('labels', [])) > 0
#                           else None, index=fset.index)
#
#        if len(data.get('pred_probs', [])) > 0:
#            preds = pd.DataFrame(data.get('pred_probs', []),
#                                 index=fset.index).to_dict(orient='index')
#        else:
#            preds = pd.Series(data['preds'], index=fset.index).to_dict()
#        result = {name: {'features': feats, 'label': labels.loc[name],
#                         'prediction': preds[name]}
#                  for name, feats in fset.to_dict(orient='index').items()}
#        return result
#
#    def display_info(self):
#        info = self.to_dict()
#        info['model_type'] = self.model.type
#        info['dataset_name'] = self.dataset.name
#        info['model_name'] = self.model.name
#        info['featureset_name'] = self.model.featureset.name
#        if self.task_id is None:
#            fset, data = featurize.load_featureset(self.file_uri)
#            info['isProbabilistic'] = (len(data['pred_probs']) > 0)
#            info['results'] = Prediction.format_pred_data(fset, data)
#        return info
#
#
#@sa.event.listens_for(DatasetFile, 'after_delete')
#def remove_dataset_file(mapper, connection, target):
#    try:
#        os.remove(target.uri)
#    except FileNotFoundError:
#        pass
