"""Ordered input lists of the single-photon BDTs (round2/config/features/*_inputs_v*.json).

The order is part of the model: TMVA readers bind inputs by position, and an XGBoost model stores no names.
"""
import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'features')


class FeatureList:
    def __init__(self, path):
        self.path = path
        with open(path) as f:
            self.cfg = json.load(f)
        self.model = self.cfg['model']
        self.inputs = self.cfg['inputs']
        if [i['index'] for i in self.inputs] != list(range(len(self.inputs))):
            raise ValueError('%s: input indices are not 0..n-1 in order' % path)
        if len(self.inputs) != self.cfg['n_inputs']:
            raise ValueError('%s: n_inputs does not match the list' % path)

    @property
    def names(self):
        """XML variable names, in model order."""
        return [i['name'] for i in self.inputs]

    @property
    def columns(self):
        """Table column that holds each input, in model order (reco_nuvtxY -> kine_nu_y_corr)."""
        return [i['table_column'] for i in self.inputs]

    @property
    def branches(self):
        return [i['caf_branch'] for i in self.inputs]

    def upstream_inputs(self):
        """Inputs that are the output of another classifier: [(index, name, producer, weights file)]."""
        return [(i['index'], i['name'], i['upstream']['producer'], i['upstream']['weights'])
                for i in self.inputs if i['kind'] == 'upstream_score']


def load(model, version='v0', config_dir=CONFIG_DIR):
    return FeatureList(os.path.join(config_dir, '%s_inputs_%s.json' % (model, version)))
