import json
import os
from datetime import datetime
from pathlib import Path
from time import sleep

import neptune
from neptune.sessions import Session
from tqdm import tqdm


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def backup_experiment(exp, destination_dir):
    destination_dir.mkdir(parents=True, exist_ok=True)

    # Parameters
    exp_params = exp.get_parameters()
    if exp_params:
        with open(destination_dir / "parameters.json", "w") as fp:
            json.dump(exp_params, fp)

    # Properties
    exp_props = exp.get_properties()
    if exp_props:
        with open(destination_dir / "properties.json", "w") as fp:
            json.dump(exp_props, fp)

    # System properties
    exp_system_props = exp.get_system_properties()
    if exp_system_props:
        with open(destination_dir / "system_properties.json", "w") as fp:
            json.dump(exp_system_props, fp, cls=DateTimeEncoder)

    # Tags
    exp_tags = exp.get_tags()
    if exp_tags:
        with open(destination_dir / "tags.json", "w") as fp:
            json.dump(exp_tags, fp)

    # Logs
    exp_logs = exp.get_logs()
    channels = [key for key in exp_logs.keys() if exp_logs[key].channelType != "image"]

    # Get log values
    df_logs = exp.get_numeric_channels_values(*channels)
    df_logs.sort_index(axis=1, inplace=True)  # sort columns
    df_logs.to_csv(destination_dir / "logs.csv", index=False)

    # Source files
    exp.download_sources(path=None, destination_dir=destination_dir)

    # Artifacts
    exp.download_artifacts(path=None, destination_dir=destination_dir)


def main():
    backup_directory = "BACKUP_FOLDER"
    namespace = ""  # Name of the workspace or username
    overwrite_existing_experiment = False

    backup_directory = Path(backup_directory)
    print("backup_directory: ", backup_directory)

    session = Session.with_default_backend()
    projects = session.get_projects(namespace)

    print(f"Found {len(projects)} project(s):")
    for i, (name, project) in enumerate(projects.items()):
        print("~~~ Project N°{}: {}".format(i, name))

        project_destination_dir = backup_directory / name
        project_destination_dir.mkdir(parents=True, exist_ok=True)
        print("project_destination_dir: ", project_destination_dir)

        experiments = project.get_experiments()
        print(f"Found {len(experiments)} experiment(s):")

        pbar = tqdm(experiments, total=len(experiments))
        for exp in pbar:
            pbar.set_description(str(exp.id))
            if exp.state == "running":
                print(f"Skip {exp.id} (still running)")
                continue
            exp_destination_dir = project_destination_dir / str(exp.id)
            if (
                not overwrite_existing_experiment
                and exp_destination_dir.exists()
                and len(os.listdir(exp_destination_dir)) > 0
            ):
                print(f"Skip {exp.id} (already exists)")
                continue  # skip since already downloaded
            backup_experiment(exp, exp_destination_dir)
            sleep(30)


if __name__ == "__main__":
    print(neptune.__version__)
    main()
