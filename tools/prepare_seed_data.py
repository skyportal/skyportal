from baselayer.app.env import load_env

import yaml

import tdtax


if __name__ == "__main__":
    env, cfg = load_env()

    with open("data/public_group.yaml", "w") as f:
        pass

    with open("data/taxonomy_sitewide.yaml", "w") as f:
        tax_obj = [{
            'name': 'Sitewide taxonomy',
            'provenance': 'https://github.com/profjsb/timedomain-taxonomy',
            'group_ids': ['=public_group_id'],
            'hierarchy': tdtax.taxonomy,
            'version': tdtax.__version__
        }]
        yaml.dump(tax_obj, f)

    with open("data/taxonomy_demo.yaml", "w") as f:
        tax_obj = [{
            'name': 'Demo taxonomy',
            'provenance': 'https://github.com/profjsb/timedomain-taxonomy',
            'group_ids': ['=program_A', '=program_B'],
            'hierarchy': tdtax.taxonomy,
            'version': tdtax.__version__
        }]
        yaml.dump(tax_obj, f)
