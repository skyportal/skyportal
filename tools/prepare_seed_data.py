import tdtax
import yaml

if __name__ == "__main__":
    with open("data/taxonomy_sitewide.yaml", "w") as f:
        tax_obj = [
            {
                "name": "Sitewide taxonomy",
                "provenance": "https://github.com/profjsb/timedomain-taxonomy",
                "group_ids": ["=public_group_id"],
                "hierarchy": tdtax.taxonomy,
                "version": str(tdtax.__version__),
            }
        ]
        yaml.dump(tax_obj, f)

    with open("data/taxonomy_demo.yaml", "w") as f:
        tax_obj = [
            {
                "name": "Demo taxonomy",
                "provenance": "https://github.com/profjsb/timedomain-taxonomy",
                "group_ids": ["=program_A", "=program_B"],
                "hierarchy": tdtax.taxonomy,
                "version": str(tdtax.__version__),
            }
        ]
        variables_taxonomy = yaml.safe_load(open("data/variable_taxonomy.yaml"))
        tax_obj.append(variables_taxonomy)
        yaml.dump(tax_obj, f)
